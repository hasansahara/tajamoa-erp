"""
tajamoa/restaurant_operations/overrides/pos_invoice.py
Override لـ POS Invoice لدعم الـ Modifiers في عملية الإرجاع
"""

import frappe
from erpnext.accounts.doctype.pos_invoice.pos_invoice import make_return_doc as _original


def make_return_doc(source_name, target_doc=None):
    """
    Override: نسخ الـ modifiers من الفاتورة الأصلية
    إلى فاتورة الإرجاع
    """
    return_doc = _original(source_name, target_doc)

    # نسخ Custom Fields من الفاتورة الأصلية
    source = frappe.get_doc("POS Invoice", source_name)
    return_doc.tajamoa_brand  = source.get("tajamoa_brand")
    return_doc.tajamoa_branch = source.get("tajamoa_branch")

    # نسخ modifiers لكل صنف
    for src_item, ret_item in zip(source.items, return_doc.items):
        ret_item.tajamoa_modifiers_json    = src_item.get("tajamoa_modifiers_json")
        ret_item.tajamoa_modifiers_display = src_item.get("tajamoa_modifiers_display")

    return return_doc
