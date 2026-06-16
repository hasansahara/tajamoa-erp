"""
tajamoa/setup/install.py
يُشغَّل تلقائياً بعد: bench --site SITE install-app tajamoa
وبعد كل: bench --site SITE migrate
"""

import frappe
from frappe import _


def after_install():
    print("→ Tajamoa: Creating roles...")
    _create_roles()

    print("→ Tajamoa: Creating workspace...")
    _create_workspace()

    print("→ Tajamoa: Creating Tajamoa Settings...")
    _create_settings_doc()

    print("→ Tajamoa: Adding custom fields...")
    from tajamoa.setup.custom_fields import create_all_custom_fields
    create_all_custom_fields()

    frappe.db.commit()
    print("✓ Tajamoa installation complete.")


def after_migrate():
    """يُشغَّل بعد كل bench migrate"""
    from tajamoa.setup.custom_fields import create_all_custom_fields
    create_all_custom_fields()
    frappe.db.commit()


# ─── الأدوار ──────────────────────────────────────────────────────────
def _create_roles():
    roles = [
        {"role_name": "Group CEO",      "desk_access": 1},
        {"role_name": "Company CFO",    "desk_access": 1},
        {"role_name": "Brand Manager",  "desk_access": 1},
        {"role_name": "Branch Manager", "desk_access": 1},
        {"role_name": "Cashier",        "desk_access": 1},
        {"role_name": "Supply Manager", "desk_access": 1},
        {"role_name": "KDS Operator",   "desk_access": 0},
    ]
    for r in roles:
        if not frappe.db.exists("Role", r["role_name"]):
            doc = frappe.new_doc("Role")
            doc.update(r)
            doc.insert(ignore_permissions=True)
            print(f"  ✓ Role created: {r['role_name']}")


# ─── Tajamoa Settings Singleton ───────────────────────────────────────
def _create_settings_doc():
    if not frappe.db.exists("DocType", "Tajamoa Settings"):
        return
    if not frappe.db.exists("Tajamoa Settings", "Tajamoa Settings"):
        doc = frappe.new_doc("Tajamoa Settings")
        doc.jareb_api_url        = "https://api.jarebtech.com/v1"
        doc.jareb_api_key        = ""
        doc.jareb_webhook_secret = ""
        doc.auto_send_to_kds     = 1
        doc.default_vat_rate     = 15.0
        doc.insert(ignore_permissions=True)
        print("  ✓ Tajamoa Settings created")


# ─── Workspace ────────────────────────────────────────────────────────
def _create_workspace():
    if frappe.db.exists("Workspace", "Restaurant Operations"):
        return
    ws = frappe.new_doc("Workspace")
    ws.update({
        "name":        "Restaurant Operations",
        "label":       "Restaurant Operations",
        "module":      "Restaurant Operations",
        "category":    "Modules",
        "is_standard": 0,
        "content":     "[]",
    })
    ws.insert(ignore_permissions=True)
    print("  ✓ Workspace created")
