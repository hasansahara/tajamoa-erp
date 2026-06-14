"""
tajamoa/restaurant_operations/api/pos_api.py
API الداخلي للـ POS المخصص — يُستدعى من Vue.js Frontend
"""

import frappe
import json
from frappe import _
from frappe.utils import now_datetime, flt


# ─── جلب إعداد الـ POS (براندات + أقسام + أصناف) ──────────────────
@frappe.whitelist()
def get_pos_config(pos_profile: str) -> dict:
    """
    نقطة بداية تحميل الـ POS:
    يعيد كل البراندات المرتبطة بالـ POS Profile مع أقسامها وأصنافها
    """
    # جلب البراندات المرتبطة بهذا الـ POS Profile
    brands_config = frappe.get_all(
        "POS Brand Config",
        filters={"pos_profile": pos_profile},
        fields=["brand", "display_order", "tab_color", "is_default"],
        order_by="display_order asc"
    )

    if not brands_config:
        frappe.throw(_("No brands configured for this POS Profile"))

    result = []
    for bc in brands_config:
        brand_doc = frappe.get_doc("Brand", bc.brand)
        sections  = _get_brand_menu(bc.brand)

        result.append({
            "brand_code":    brand_doc.brand_code,
            "brand_name":    brand_doc.name,
            "brand_name_ar": brand_doc.brand_name_ar or brand_doc.brand_name,
            "brand_name_en": brand_doc.brand_name,
            "brand_color":   bc.tab_color or brand_doc.brand_color or "#1D3557",
            "brand_logo":    brand_doc.brand_logo,
            "is_default":    bc.is_default,
            "display_order": bc.display_order,
            "cost_center":   brand_doc.cost_center,
            "company":       brand_doc.company,
            "sections":      sections,
        })

    return {
        "brands":      result,
        "pos_profile": pos_profile,
        "currency":    frappe.defaults.get_global_default("currency") or "SAR",
        "vat_rate":    frappe.db.get_single_value("Tajamoa Settings", "default_vat_rate") or 15,
    }


def _get_brand_menu(brand: str) -> list:
    """جلب أقسام وأصناف البراند كاملةً"""
    sections = frappe.get_all(
        "Menu Section",
        filters={"brand": brand, "is_active": 1},
        fields=["name", "section_name_ar", "section_name_en",
                "section_icon", "sort_order"],
        order_by="sort_order asc"
    )

    for sec in sections:
        items = frappe.get_all(
            "Menu Item",
            filters={
                "brand":        brand,
                "menu_section": sec.name,
                "is_available": 1,
            },
            fields=[
                "name", "display_name_ar", "display_name_en",
                "description_ar", "base_price", "thumbnail",
                "item_image", "calories", "prep_time_mins",
                "is_featured", "sort_order", "kitchen_station",
            ],
            order_by="sort_order asc"
        )

        for item in items:
            item["modifiers"] = _get_item_modifiers(item.name)

        sec["items"] = items

    return sections


def _get_item_modifiers(menu_item: str) -> list:
    """جلب modifier groups لصنف معين"""
    links = frappe.get_all(
        "Menu Item Modifier Link",
        filters={"parent": menu_item},
        fields=["modifier_group", "sort_order"],
        order_by="sort_order asc"
    )
    groups = []
    for link in links:
        grp  = frappe.get_doc("Modifier Group", link.modifier_group)
        opts = [
            {
                "name":          opt.name,
                "option_name_ar": opt.option_name_ar,
                "option_name_en": opt.option_name_en,
                "price_addition": flt(opt.price_addition),
                "is_default":    opt.is_default,
                "is_available":  opt.is_available,
            }
            for opt in grp.options if opt.is_available
        ]
        groups.append({
            "name":           grp.name,
            "group_name_ar":  grp.group_name_ar,
            "group_name_en":  grp.group_name_en,
            "selection_type": grp.selection_type,
            "is_required":    grp.is_required,
            "min_selection":  grp.min_selection,
            "max_selection":  grp.max_selection,
            "options":        opts,
        })
    return groups


# ─── إنشاء / تحديث Table Order ───────────────────────────────────────
@frappe.whitelist()
def save_order(order_data: str) -> dict:
    """
    حفظ أو تحديث Table Order من واجهة الـ POS.
    order_data: JSON string
    """
    data = json.loads(order_data)
    order_name = data.get("name")

    if order_name and frappe.db.exists("Table Order", order_name):
        order = frappe.get_doc("Table Order", order_name)
        order.items = []      # مسح القديم وإعادة البناء
    else:
        order = frappe.new_doc("Table Order")

    order.update({
        "brand":         data.get("brand"),
        "order_type":    data.get("order_type", "Dine-In"),
        "dining_table":  data.get("dining_table"),
        "cover_count":   data.get("cover_count", 1),
        "pos_profile":   data.get("pos_profile"),
        "payment_method": data.get("payment_method", ""),
        "notes":         data.get("notes", ""),
    })

    # الأصناف
    for it in data.get("items", []):
        modifiers_json = json.dumps(it.get("modifiers", []), ensure_ascii=False)
        modifiers_display = ", ".join(
            m.get("option_name_ar", "") for m in it.get("modifiers", [])
        )
        modifiers_total = sum(
            flt(m.get("price_addition", 0)) for m in it.get("modifiers", [])
        )
        qty = flt(it.get("qty", 1))
        unit_price = flt(it.get("unit_price", 0))

        order.append("items", {
            "menu_item":         it.get("menu_item"),
            "item_name_ar":      it.get("item_name_ar"),
            "qty":               qty,
            "unit_price":        unit_price,
            "modifiers_json":    modifiers_json,
            "modifiers_display": modifiers_display,
            "modifiers_total":   modifiers_total,
            "line_total":        (unit_price + modifiers_total) * qty,
            "item_notes":        it.get("item_notes", ""),
            "kitchen_station":   it.get("kitchen_station", ""),
            "kds_status":        "Pending",
        })

    # الإجماليات
    subtotal = sum(flt(i.line_total) for i in order.items)
    vat_rate = flt(frappe.db.get_single_value("Tajamoa Settings", "default_vat_rate") or 15)
    discount = flt(data.get("discount_amount", 0))
    tax_amount = round((subtotal - discount) * vat_rate / 100, 2)

    order.subtotal       = subtotal
    order.discount_amount = discount
    order.tax_amount     = tax_amount
    order.total          = subtotal - discount + tax_amount

    order.save(ignore_permissions=True)

    return {
        "name":     order.name,
        "subtotal": order.subtotal,
        "tax":      order.tax_amount,
        "total":    order.total,
        "status":   order.status,
    }


# ─── إرسال للمطبخ ────────────────────────────────────────────────────
@frappe.whitelist()
def send_to_kitchen(order_name: str) -> dict:
    order = frappe.get_doc("Table Order", order_name)
    if order.status not in ("Draft",):
        frappe.throw(_(f"Cannot send order in status: {order.status}"))

    order.status           = "Sent to Kitchen"
    order.kitchen_sent_time = now_datetime()
    order.save(ignore_permissions=True)

    # Realtime إلى KDS
    frappe.publish_realtime(
        event="kitchen_order",
        message={
            "order":    order.name,
            "brand":    order.brand,
            "items":    [
                {
                    "item_name_ar":      i.item_name_ar,
                    "qty":               i.qty,
                    "modifiers_display": i.modifiers_display,
                    "item_notes":        i.item_notes,
                    "kitchen_station":   i.kitchen_station,
                }
                for i in order.items
            ],
            "order_type": order.order_type,
            "table":     order.dining_table,
            "timestamp": str(now_datetime()),
        },
        room=f"kds_{order.brand}"
    )

    return {"status": "Sent to Kitchen", "order": order.name}


# ─── تحويل الطلب لـ POS Invoice ──────────────────────────────────────
@frappe.whitelist()
def checkout(order_name: str, payment_method: str) -> dict:
    """
    إغلاق الطلب وإنشاء POS Invoice في ERPNext
    """
    order = frappe.get_doc("Table Order", order_name)
    brand = frappe.get_doc("Brand", order.brand)

    # إنشاء POS Invoice
    invoice = frappe.new_doc("POS Invoice")
    invoice.update({
        "company":            brand.company,
        "pos_profile":        order.pos_profile,
        "customer":           "Walk-In Customer",   # أو من CRM
        "tajamoa_table_order": order.name,
        "tajamoa_brand":      order.brand,
        "cost_center":        brand.cost_center,
        "delivery_source":    order.delivery_source or "",
        "posting_date":       frappe.utils.today(),
        "posting_time":       frappe.utils.nowtime(),
    })

    for it in order.items:
        invoice.append("items", {
            "item_code":                  it.menu_item,
            "item_name":                  it.item_name_ar,
            "qty":                        it.qty,
            "rate":                       it.unit_price + it.modifiers_total,
            "cost_center":                brand.cost_center,
            "tajamoa_modifiers_json":     it.modifiers_json,
            "tajamoa_modifiers_display":  it.modifiers_display,
        })

    invoice.append("payments", {
        "mode_of_payment": payment_method,
        "amount":          order.total,
    })

    invoice.insert(ignore_permissions=True)
    invoice.submit()

    # تحديث الطلب
    order.status      = "Billed"
    order.closed_time = now_datetime()
    order.pos_invoice = invoice.name
    order.save(ignore_permissions=True)

    # تحرير الطاولة إن وجدت
    if order.dining_table:
        frappe.db.set_value("Dining Table", order.dining_table, "status", "Available")
        frappe.db.set_value("Dining Table", order.dining_table, "current_order", None)

    return {
        "pos_invoice": invoice.name,
        "total":       order.total,
        "status":      "Billed",
    }


# ─── جلب حالة الطاولات ───────────────────────────────────────────────
@frappe.whitelist()
def get_tables(brand: str) -> list:
    return frappe.get_all(
        "Dining Table",
        filters={"brand": brand, "is_active": 1},
        fields=["name", "table_name", "capacity", "status",
                "current_order", "floor_section", "pos_x", "pos_y"],
        order_by="table_name asc"
    )
