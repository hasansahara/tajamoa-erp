"""
tajamoa/restaurant_operations/api/menu_sync.py
مزامنة المنيو من ERPNext إلى جرب تك
"""

import frappe
import requests
import json
from frappe import _
from frappe.utils import now_datetime


# ─── مزامنة براند واحد ───────────────────────────────────────────────
@frappe.whitelist()
def push_menu(brand_code: str) -> dict:
    """
    ادفع منيو براند معين إلى جرب تك.
    يُستدعى يدوياً من واجهة ERPNext أو تلقائياً.
    """
    brand = frappe.get_doc("Brand", brand_code)
    if not brand.jareb_brand_id:
        frappe.throw(_(f"Brand {brand_code} has no Jareb Brand ID"))

    menu_payload = _build_menu_payload(brand)
    response     = _send_to_jareb(brand, menu_payload)

    # تحديث last_synced على كل Menu Item
    frappe.db.set_value(
        "Menu Item",
        {"brand": brand.name, "is_available": 1},
        "last_synced",
        now_datetime()
    )
    frappe.db.commit()

    return {
        "brand": brand.name,
        "items_sent": len(menu_payload.get("items", [])),
        "jareb_response": response.get("status"),
    }


# ─── مزامنة تلقائية لكل البراندات (Scheduled) ───────────────────────
def auto_sync_all_brands():
    """تُشغَّل كل ساعة بواسطة Scheduler"""
    brands = frappe.get_all(
        "Brand",
        filters={"is_active": 1, "jareb_brand_id": ["!=", ""]},
        pluck="name"
    )
    results = []
    for brand_name in brands:
        try:
            result = push_menu(brand_name)
            results.append({"brand": brand_name, "status": "OK", **result})
        except Exception as e:
            frappe.log_error(
                f"Menu sync failed for {brand_name}: {str(e)}",
                "Jareb Menu Sync"
            )
            results.append({"brand": brand_name, "status": "FAILED", "error": str(e)})
    return results


# ─── بناء الـ Payload للإرسال ─────────────────────────────────────────
def _build_menu_payload(brand) -> dict:
    sections = frappe.get_all(
        "Menu Section",
        filters={"brand": brand.name, "is_active": 1},
        fields=["name", "section_name_ar", "section_name_en", "sort_order"],
        order_by="sort_order asc"
    )

    payload_sections = []
    for section in sections:
        items = frappe.get_all(
            "Menu Item",
            filters={
                "brand": brand.name,
                "menu_section": section.name,
                "is_available": 1
            },
            fields=[
                "name", "display_name_ar", "display_name_en",
                "description_ar", "base_price", "item_image",
                "calories", "prep_time_mins", "jareb_item_id",
                "sort_order"
            ],
            order_by="sort_order asc"
        )

        payload_items = []
        for item in items:
            modifier_groups = _get_modifier_groups(item.name)
            payload_items.append({
                "id":           item.jareb_item_id or item.name,
                "name_ar":      item.display_name_ar,
                "name_en":      item.display_name_en,
                "description":  item.description_ar or "",
                "price":        float(item.base_price),
                "image_url":    _get_full_url(item.item_image),
                "calories":     item.calories or 0,
                "prep_time":    item.prep_time_mins or 10,
                "modifiers":    modifier_groups,
                "available":    True,
            })

        payload_sections.append({
            "id":      section.name,
            "name_ar": section.section_name_ar,
            "name_en": section.section_name_en,
            "items":   payload_items,
        })

    return {
        "restaurant_id": brand.jareb_brand_id,
        "sections":       payload_sections,
    }


def _get_modifier_groups(menu_item_name: str) -> list:
    """جلب كل modifier groups الخاصة بصنف معين"""
    links = frappe.get_all(
        "Menu Item Modifier Link",
        filters={"parent": menu_item_name},
        fields=["modifier_group", "sort_order"],
        order_by="sort_order asc"
    )

    groups = []
    for link in links:
        grp = frappe.get_doc("Modifier Group", link.modifier_group)
        options = []
        for opt in grp.options:
            if opt.is_available:
                options.append({
                    "id":         opt.name,
                    "name_ar":    opt.option_name_ar,
                    "name_en":    opt.option_name_en,
                    "price":      float(opt.price_addition or 0),
                    "is_default": bool(opt.is_default),
                })
        groups.append({
            "id":           grp.name,
            "name_ar":      grp.group_name_ar,
            "name_en":      grp.group_name_en,
            "type":         grp.selection_type.lower(),   # "single" / "multiple"
            "required":     bool(grp.is_required),
            "min":          grp.min_selection or 0,
            "max":          grp.max_selection or 1,
            "options":      options,
        })
    return groups


def _send_to_jareb(brand, payload: dict) -> dict:
    settings  = frappe.get_single("Tajamoa Settings")
    base_url  = settings.jareb_api_url.rstrip("/")
    api_key   = settings.jareb_api_key
    headers   = {
        "Content-Type":  "application/json",
        "Authorization": f"Bearer {api_key}",
        "X-Brand-ID":    brand.jareb_brand_id,
    }
    resp = requests.post(
        f"{base_url}/menu/update",
        json=payload,
        headers=headers,
        timeout=30
    )
    resp.raise_for_status()
    return resp.json()


def _get_full_url(path: str) -> str:
    if not path:
        return ""
    if path.startswith("http"):
        return path
    site_url = frappe.utils.get_url()
    return f"{site_url}{path}"
