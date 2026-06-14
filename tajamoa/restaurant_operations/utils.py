"""
tajamoa/restaurant_operations/utils.py
Jinja helper functions referenced in hooks.py
"""

import frappe


def get_brand_logo(brand_name: str) -> str:
    """Returns the full URL of a brand's logo — used in print templates"""
    if not brand_name:
        return ""
    logo = frappe.db.get_value("Brand", brand_name, "brand_logo")
    if not logo:
        return ""
    if logo.startswith("http"):
        return logo
    return f"{frappe.utils.get_url()}{logo}"


def format_order_items(items) -> str:
    """Returns a human-readable summary of order items — used in print templates"""
    if not items:
        return ""
    lines = []
    for item in items:
        line = f"{item.get('qty', 1)}x {item.get('item_name_ar') or item.get('item_name', '')}"
        mods = item.get("modifiers_display") or item.get("tajamoa_modifiers_display", "")
        if mods:
            line += f" ({mods})"
        lines.append(line)
    return " | ".join(lines)
