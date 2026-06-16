"""
tajamoa/setup/custom_fields.py
إضافة حقول مخصصة على Branch (ERPNext Setup module)
وعلى POS Invoice و Item
"""

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


# ─── تعريف كل الـ Custom Fields ────────────────────────────────────────
CUSTOM_FIELDS = {

    # ══════════════════════════════════════════════════════
    # Branch — نضيف عليه كل ما يخص الفرع
    # ══════════════════════════════════════════════════════
    "Branch": [
        {
            "fieldname": "tajamoa_section",
            "fieldtype": "Section Break",
            "label": "إعدادات تجمعة",
            "insert_after": "branch",
        },
        {
            "fieldname": "company",
            "fieldtype": "Link",
            "label": "الشركة",
            "options": "Company",
            "reqd": 1,
            "insert_after": "tajamoa_section",
            "in_list_view": 1,
        },
        {
            "fieldname": "warehouse",
            "fieldtype": "Link",
            "label": "المستودع",
            "options": "Warehouse",
            "insert_after": "company",
            "description": "المستودع المرتبط بهذا الفرع للمخزون",
        },
        {
            "fieldname": "col_break_1",
            "fieldtype": "Column Break",
            "insert_after": "warehouse",
        },
        {
            "fieldname": "pos_profile",
            "fieldtype": "Link",
            "label": "POS Profile",
            "options": "POS Profile",
            "insert_after": "col_break_1",
            "description": "نقطة البيع الرئيسية لهذا الفرع",
        },
        {
            "fieldname": "cost_center",
            "fieldtype": "Link",
            "label": "Cost Center",
            "options": "Cost Center",
            "insert_after": "pos_profile",
            "description": "مركز التكلفة المحاسبي للفرع",
        },
        {
            "fieldname": "branch_type",
            "fieldtype": "Select",
            "label": "نوع الفرع",
            "options": "Main Branch\nCloud Kitchen\nDark Kitchen\nKiosk",
            "default": "Main Branch",
            "insert_after": "cost_center",
            "in_list_view": 1,
        },
        {
            "fieldname": "brands_section",
            "fieldtype": "Section Break",
            "label": "البراندات في هذا الفرع",
            "insert_after": "branch_type",
        },
        {
            "fieldname": "brands",
            "fieldtype": "Table",
            "label": "البراندات",
            "options": "Branch Brand Link",
            "insert_after": "brands_section",
            "description": "البراندات التي تعمل داخل هذا الفرع — تظهر كتبويبات في POS",
        },
        {
            "fieldname": "location_section",
            "fieldtype": "Section Break",
            "label": "الموقع",
            "insert_after": "brands",
        },
        {
            "fieldname": "city",
            "fieldtype": "Data",
            "label": "المدينة",
            "insert_after": "location_section",
            "in_list_view": 1,
        },
        {
            "fieldname": "district",
            "fieldtype": "Data",
            "label": "الحي",
            "insert_after": "city",
        },
        {
            "fieldname": "col_break_2",
            "fieldtype": "Column Break",
            "insert_after": "district",
        },
        {
            "fieldname": "address",
            "fieldtype": "Small Text",
            "label": "العنوان الكامل",
            "insert_after": "col_break_2",
        },
        {
            "fieldname": "google_maps_url",
            "fieldtype": "Data",
            "label": "رابط خرائط Google",
            "insert_after": "address",
        },
        {
            "fieldname": "operations_section",
            "fieldtype": "Section Break",
            "label": "التشغيل",
            "insert_after": "google_maps_url",
        },
        {
            "fieldname": "opening_time",
            "fieldtype": "Time",
            "label": "وقت الفتح",
            "insert_after": "operations_section",
        },
        {
            "fieldname": "closing_time",
            "fieldtype": "Time",
            "label": "وقت الإغلاق",
            "insert_after": "opening_time",
        },
        {
            "fieldname": "col_break_3",
            "fieldtype": "Column Break",
            "insert_after": "closing_time",
        },
        {
            "fieldname": "is_active",
            "fieldtype": "Check",
            "label": "نشط",
            "default": "1",
            "insert_after": "col_break_3",
            "in_list_view": 1,
        },
        {
            "fieldname": "accepts_delivery",
            "fieldtype": "Check",
            "label": "يقبل التوصيل",
            "default": "1",
            "insert_after": "is_active",
        },
        {
            "fieldname": "accepts_dine_in",
            "fieldtype": "Check",
            "label": "يقبل الجلوس",
            "default": "1",
            "insert_after": "accepts_delivery",
        },
    ],

    # ══════════════════════════════════════════════════════
    # POS Invoice — ربط الفاتورة بالفرع والبراند
    # ══════════════════════════════════════════════════════
    "POS Invoice": [
        {
            "fieldname": "tajamoa_table_order",
            "fieldtype": "Link",
            "label": "Table Order",
            "options": "Table Order",
            "insert_after": "pos_profile",
            "read_only": 1,
        },
        {
            "fieldname": "tajamoa_brand",
            "fieldtype": "Link",
            "label": "Brand",
            "options": "Brand",
            "insert_after": "tajamoa_table_order",
            "in_list_view": 1,
        },
        {
            "fieldname": "tajamoa_branch",
            "fieldtype": "Link",
            "label": "Branch",
            "options": "Branch",
            "insert_after": "tajamoa_brand",
            "in_list_view": 1,
        },
        {
            "fieldname": "delivery_source",
            "fieldtype": "Select",
            "label": "مصدر التوصيل",
            "options": "\nJareb Tech\nHunger Station\nJahez\nToter\nMrsool\nDirect",
            "insert_after": "tajamoa_branch",
            "read_only": 1,
        },
    ],

    # ══════════════════════════════════════════════════════
    # POS Invoice Item — حفظ الـ Modifiers في الفاتورة
    # ══════════════════════════════════════════════════════
    "POS Invoice Item": [
        {
            "fieldname": "tajamoa_modifiers_json",
            "fieldtype": "Long Text",
            "label": "Modifiers JSON",
            "insert_after": "item_name",
            "hidden": 1,
        },
        {
            "fieldname": "tajamoa_modifiers_display",
            "fieldtype": "Small Text",
            "label": "الإضافات المختارة",
            "insert_after": "tajamoa_modifiers_json",
            "read_only": 1,
        },
    ],

    # ══════════════════════════════════════════════════════
    # Item — ربط الصنف بالبراند الأساسي
    # ══════════════════════════════════════════════════════
    "Item": [
        {
            "fieldname": "tajamoa_brand",
            "fieldtype": "Link",
            "label": "Primary Brand",
            "options": "Brand",
            "insert_after": "item_group",
        },
        {
            "fieldname": "tajamoa_item_type",
            "fieldtype": "Select",
            "label": "Item Type (Tajamoa)",
            "options": "\nFinal Product\nRaw Material\nPackaging\nCleaning\nSemi-Finished",
            "insert_after": "tajamoa_brand",
        },
    ],

    # ══════════════════════════════════════════════════════
    # Table Order — إضافة حقل الفرع
    # ══════════════════════════════════════════════════════
    "Table Order": [
        {
            "fieldname": "branch",
            "fieldtype": "Link",
            "label": "Branch",
            "options": "Branch",
            "insert_after": "brand",
            "in_list_view": 1,
            "reqd": 0,
        },
    ],
}


# ─── الدالة الرئيسية — تُستدعى من install.py ───────────────────────
def create_all_custom_fields():
    """
    أنشئ أو حدّث كل الـ Custom Fields.
    تُشغَّل عند التثبيت وعند كل migrate.
    """
    try:
        create_custom_fields(CUSTOM_FIELDS, ignore_validate=True)
        frappe.db.commit()
        frappe.logger().info("Tajamoa: custom fields created/updated successfully")
    except Exception as e:
        frappe.logger().error(f"Tajamoa custom fields error: {e}")
        raise


# ─── حذف Custom Fields عند إزالة التطبيق ──────────────────────────
def delete_all_custom_fields():
    """تُستدعى قبل إزالة التطبيق"""
    for doctype, fields in CUSTOM_FIELDS.items():
        for field in fields:
            fname = field["fieldname"]
            cf_name = f"{doctype}-{fname}"
            if frappe.db.exists("Custom Field", cf_name):
                frappe.delete_doc("Custom Field", cf_name, ignore_permissions=True)
    frappe.db.commit()
