"""
tajamoa/restaurant_operations/api/jareb_webhook.py
استقبال طلبات جرب تك وتحويلها لـ Table Order + Sales Order في ERPNext
"""

import frappe
import json
from frappe import _
from frappe.utils import now_datetime


# ─── الـ Endpoint الرئيسي ────────────────────────────────────────────
@frappe.whitelist(allow_guest=True, methods=["POST"])
def receive():
    """
    Endpoint: /api/jareb/webhook
    يستقبل طلبات جرب تك ويحولها لـ Table Order
    """
    try:
        # التحقق من الـ token
        _verify_jareb_token()

        payload = json.loads(frappe.request.data or "{}")
        event_type = payload.get("event_type", "")

        handlers = {
            "order.created":   _handle_new_order,
            "order.cancelled": _handle_cancelled_order,
            "order.updated":   _handle_updated_order,
        }

        handler = handlers.get(event_type)
        if not handler:
            frappe.log_error(
                f"Unknown Jareb event: {event_type}",
                "Jareb Webhook"
            )
            return _response(400, f"Unknown event type: {event_type}")

        result = handler(payload)
        return _response(200, "OK", result)

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Jareb Webhook Error")
        return _response(500, str(e))


# ─── معالجة طلب جديد ─────────────────────────────────────────────────
def _handle_new_order(payload: dict) -> dict:
    order_data = payload.get("order", {})
    brand_code  = payload.get("brand_code", "")

    # جلب الـ Brand من ERPNext
    brand = frappe.get_value(
        "Brand",
        {"jareb_brand_id": payload.get("restaurant_id")},
        ["name", "company", "cost_center"],
        as_dict=True
    )
    if not brand:
        frappe.throw(_(f"Brand not found for Jareb restaurant_id: {payload.get('restaurant_id')}"))

    # بناء قائمة الأصناف
    items = []
    for line in order_data.get("items", []):
        modifiers = []
        modifier_total = 0.0

        for mod in line.get("modifiers", []):
            mod_price = float(mod.get("price", 0))
            modifiers.append({
                "group":          mod.get("group_id"),
                "group_name_ar":  mod.get("group_name"),
                "option":         mod.get("option_id"),
                "option_name_ar": mod.get("option_name"),
                "price_addition": mod_price,
            })
            modifier_total += mod_price

        unit_price = float(line.get("unit_price", 0))

        items.append({
            "menu_item":        _find_menu_item(line.get("item_id"), brand.name),
            "item_name_ar":     line.get("item_name"),
            "qty":              float(line.get("qty", 1)),
            "unit_price":       unit_price,
            "modifiers_json":   json.dumps(modifiers, ensure_ascii=False),
            "modifiers_display": ", ".join([m["option_name_ar"] for m in modifiers]),
            "modifiers_total":  modifier_total,
            "line_total":       (unit_price + modifier_total) * float(line.get("qty", 1)),
            "item_notes":       line.get("notes", ""),
            "kds_status":       "Pending",
        })

    # إنشاء Table Order
    order = frappe.new_doc("Table Order")
    order.update({
        "brand":                brand.name,
        "order_type":           "Delivery",
        "status":               "Draft",
        "delivery_source":      _map_delivery_source(payload.get("platform", "")),
        "external_order_id":    str(order_data.get("id", "")),
        "customer_name_delivery": order_data.get("customer", {}).get("name", ""),
        "customer_phone":       order_data.get("customer", {}).get("phone", ""),
        "delivery_address":     order_data.get("delivery_address", {}).get("full_address", ""),
        "subtotal":             float(order_data.get("subtotal", 0)),
        "discount_amount":      float(order_data.get("discount", 0)),
        "tax_amount":           float(order_data.get("tax", 0)),
        "total":                float(order_data.get("total", 0)),
        "order_time":           now_datetime(),
        "items":                items,
    })
    order.insert(ignore_permissions=True)

    # إرسال فورياً للمطبخ عبر Realtime
    frappe.publish_realtime(
        event="new_delivery_order",
        message={"order": order.name, "brand": brand.name},
        room=f"brand_{brand.name}"
    )

    return {"table_order": order.name}


# ─── إلغاء طلب ───────────────────────────────────────────────────────
def _handle_cancelled_order(payload: dict) -> dict:
    external_id = str(payload.get("order", {}).get("id", ""))
    order_name  = frappe.get_value(
        "Table Order",
        {"external_order_id": external_id},
        "name"
    )
    if order_name:
        order = frappe.get_doc("Table Order", order_name)
        order.status = "Cancelled"
        order.save(ignore_permissions=True)
        frappe.publish_realtime(
            "order_cancelled",
            {"order": order_name},
            room=f"brand_{order.brand}"
        )
    return {"cancelled": order_name}


# ─── تحديث طلب ───────────────────────────────────────────────────────
def _handle_updated_order(payload: dict) -> dict:
    # يمكن التوسع لاحقاً
    return {"status": "acknowledged"}


# ─── دوال مساعدة ─────────────────────────────────────────────────────
def _find_menu_item(jareb_item_id: str, brand: str) -> str:
    """ابحث عن Menu Item بالـ jareb_item_id والبراند"""
    return frappe.get_value(
        "Menu Item",
        {"jareb_item_id": jareb_item_id, "brand": brand},
        "name"
    ) or ""


def _map_delivery_source(platform: str) -> str:
    mapping = {
        "hungerstation": "Hunger Station",
        "jahez":         "Jahez",
        "toter":         "Toter",
        "mrsool":        "Mrsool",
    }
    return mapping.get(platform.lower(), "Jareb Tech")


def _verify_jareb_token():
    """تحقق من Webhook Secret Token"""
    expected = frappe.db.get_single_value("Tajamoa Settings", "jareb_webhook_secret")
    received = frappe.request.headers.get("X-Jareb-Signature", "")
    if expected and received != expected:
        frappe.throw(_("Invalid webhook signature"), frappe.AuthenticationError)


def _response(status: int, message: str, data: dict = None) -> dict:
    frappe.response["http_status_code"] = status
    return {"status": status, "message": message, "data": data or {}}


# ─── Hook: عند إنشاء Sales Order تلقائياً ───────────────────────────
def on_order_created(doc, method):
    """يُستدعى من hooks عند إنشاء Sales Order من مصدر خارجي"""
    pass
