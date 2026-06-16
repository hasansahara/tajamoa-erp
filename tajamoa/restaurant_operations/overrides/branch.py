"""
tajamoa/restaurant_operations/overrides/branch.py
منطق إضافي على الـ Branch doctype عبر doc_events في hooks.py
"""

import frappe
from frappe import _


def on_update(doc, method):
    """
    يُشغَّل عند حفظ أي Branch.
    - يتحقق من وجود براند افتراضي واحد فقط
    - يحدث POS Brand Config تلقائياً
    """
    _validate_single_default_brand(doc)
    _sync_pos_brand_config(doc)


def _validate_single_default_brand(doc):
    """يتأكد أن براند واحد فقط هو الافتراضي"""
    defaults = [b for b in (doc.get("brands") or []) if b.is_default]
    if len(defaults) > 1:
        frappe.throw(
            _("يمكن تحديد براند افتراضي واحد فقط لكل فرع. تم تحديد {0} براندات كافتراضية.").format(
                len(defaults)
            )
        )


def _sync_pos_brand_config(doc):
    """
    عند حفظ الفرع يتم تحديث POS Brand Config تلقائياً
    لكل براند في جدول البراندات
    """
    pos_profile = doc.get("pos_profile")
    if not pos_profile:
        return

    brands = doc.get("brands") or []
    if not brands:
        return

    for idx, row in enumerate(brands):
        if not row.brand or not row.is_active:
            continue

        existing = frappe.db.get_value(
            "POS Brand Config",
            {"pos_profile": pos_profile, "brand": row.brand},
            "name",
        )

        if existing:
            frappe.db.set_value("POS Brand Config", existing, {
                "display_order": row.display_order or idx,
                "tab_color":     row.tab_color or "",
                "is_default":    row.is_default or 0,
            })
        else:
            config = frappe.new_doc("POS Brand Config")
            config.update({
                "pos_profile":   pos_profile,
                "brand":         row.brand,
                "display_order": row.display_order or idx,
                "tab_color":     row.tab_color or "",
                "is_default":    row.is_default or 0,
            })
            config.insert(ignore_permissions=True)

    frappe.db.commit()


# ─── API: جلب البراندات الخاصة بفرع معين ──────────────────────────
@frappe.whitelist()
def get_branch_brands(branch: str) -> list:
    """
    يُستدعى من POS عند اختيار الفرع.
    يعيد قائمة البراندات مرتبة حسب display_order.
    """
    doc = frappe.get_doc("Branch", branch)
    brands = []

    for row in sorted(doc.get("brands") or [], key=lambda x: x.display_order or 0):
        if not row.is_active or not row.brand:
            continue

        brand_doc = frappe.get_doc("Brand", row.brand)
        brands.append({
            "brand":         row.brand,
            "brand_name_ar": brand_doc.brand_name_ar or brand_doc.brand_name,
            "brand_name_en": brand_doc.brand_name,
            "brand_code":    brand_doc.brand_code,
            "brand_color":   row.tab_color or brand_doc.brand_color or "#1D3557",
            "brand_logo":    brand_doc.brand_logo,
            "is_default":    row.is_default,
            "display_order": row.display_order,
            "cost_center":   brand_doc.cost_center,
            "company":       brand_doc.company,
        })

    return brands


# ─── API: جلب كل الفروع النشطة لشركة معينة ────────────────────────
@frappe.whitelist()
def get_active_branches(company: str = None) -> list:
    filters = {"is_active": 1}
    if company:
        filters["company"] = company

    branches = frappe.get_all(
        "Branch",
        filters=filters,
        fields=["name", "company", "city", "district",
                "pos_profile", "cost_center", "branch_type"],
        order_by="name asc",
    )
    return branches
