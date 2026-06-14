"""
tajamoa/setup/install.py
يُشغَّل تلقائياً بعد: bench --site SITE install-app tajamoa
"""

import frappe
from frappe import _


def after_install():
    """إعداد التطبيق الأولي بعد التثبيت"""
    print("→ Tajamoa: Setting up roles...")
    _create_roles()

    print("→ Tajamoa: Creating default workspace...")
    _create_workspace()

    print("→ Tajamoa: Creating Tajamoa Settings singleton...")
    _create_settings()

    print("→ Tajamoa: Setting up custom fields on ERPNext doctypes...")
    _add_custom_fields()

    frappe.db.commit()
    print("✓ Tajamoa installation complete.")


def after_migrate():
    """يُشغَّل بعد كل bench migrate"""
    _add_custom_fields()
    frappe.db.commit()


# ─── الأدوار ──────────────────────────────────────────────────────────
def _create_roles():
    roles = [
        {"role_name": "Group CEO",       "desk_access": 1},
        {"role_name": "Company CFO",     "desk_access": 1},
        {"role_name": "Brand Manager",   "desk_access": 1},
        {"role_name": "Branch Manager",  "desk_access": 1},
        {"role_name": "Cashier",         "desk_access": 1},
        {"role_name": "Supply Manager",  "desk_access": 1},
        {"role_name": "KDS Operator",    "desk_access": 0},
    ]
    for r in roles:
        if not frappe.db.exists("Role", r["role_name"]):
            doc = frappe.new_doc("Role")
            doc.update(r)
            doc.insert(ignore_permissions=True)


# ─── إعدادات الـ Singleton ────────────────────────────────────────────
def _create_settings():
    if not frappe.db.exists("DocType", "Tajamoa Settings"):
        return
    if not frappe.db.exists("Tajamoa Settings", "Tajamoa Settings"):
        doc = frappe.new_doc("Tajamoa Settings")
        doc.jareb_api_url           = "https://api.jarebtech.com/v1"
        doc.jareb_api_key           = ""
        doc.jareb_webhook_secret    = ""
        doc.auto_send_to_kds        = 1
        doc.default_vat_rate        = 15.0
        doc.insert(ignore_permissions=True)


# ─── حقول مخصصة على Doctypes ERPNext ─────────────────────────────────
def _add_custom_fields():
    """
    إضافة حقول على POS Invoice و Item لدعم الـ Modifiers
    بدلاً من تعديل الـ Doctypes الأصلية مباشرةً
    """
    custom_fields = {
        # حقل ربط POS Invoice بـ Table Order
        "POS Invoice": [
            {
                "fieldname": "tajamoa_table_order",
                "fieldtype": "Link",
                "label":     "Table Order",
                "options":   "Table Order",
                "insert_after": "pos_profile",
                "read_only": 1,
            },
            {
                "fieldname": "tajamoa_brand",
                "fieldtype": "Link",
                "label":     "Brand",
                "options":   "Brand",
                "insert_after": "tajamoa_table_order",
                "in_list_view": 1,
            },
            {
                "fieldname": "delivery_source",
                "fieldtype": "Data",
                "label":     "Delivery Source",
                "insert_after": "tajamoa_brand",
                "read_only": 1,
            },
        ],
        # حقل ربط POS Invoice Item بالـ Modifiers
        "POS Invoice Item": [
            {
                "fieldname": "tajamoa_modifiers_json",
                "fieldtype": "Long Text",
                "label":     "Modifiers (JSON)",
                "insert_after": "item_name",
                "hidden":    1,
            },
            {
                "fieldname": "tajamoa_modifiers_display",
                "fieldtype": "Small Text",
                "label":     "الإضافات المختارة",
                "insert_after": "tajamoa_modifiers_json",
                "read_only": 1,
            },
        ],
        # حقل البراند على Item
        "Item": [
            {
                "fieldname": "tajamoa_brand",
                "fieldtype": "Link",
                "label":     "Primary Brand",
                "options":   "Brand",
                "insert_after": "item_group",
                "in_list_view": 0,
            },
        ],
    }

    for doctype, fields in custom_fields.items():
        for field_def in fields:
            fname = field_def["fieldname"]
            if not frappe.db.exists("Custom Field", f"{doctype}-{fname}"):
                cf = frappe.new_doc("Custom Field")
                cf.dt = doctype
                cf.update(field_def)
                cf.insert(ignore_permissions=True)


# ─── Workspace ────────────────────────────────────────────────────────
def _create_workspace():
    if frappe.db.exists("Workspace", "Restaurant Operations"):
        return
    ws = frappe.new_doc("Workspace")
    ws.update({
        "name":     "Restaurant Operations",
        "label":    "Restaurant Operations",
        "module":   "Restaurant Operations",
        "category": "Modules",
        "is_standard": 0,
        "content":  "[]",
    })
    ws.insert(ignore_permissions=True)
