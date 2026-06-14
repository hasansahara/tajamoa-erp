"""
tajamoa/restaurant_operations/permissions.py
Row-level permission conditions — referenced in hooks.py
"""

import frappe


def brand_query(user, doctype=None):
    """
    يُقيّد المستخدم برؤية البراندات المرتبطة بشركته فقط.
    System Manager و Group CEO يرون الكل.
    """
    if not user:
        user = frappe.session.user

    # System Manager يرى الكل
    if "System Manager" in frappe.get_roles(user):
        return ""

    # Group CEO يرى الكل (قراءة فقط)
    if "Group CEO" in frappe.get_roles(user):
        return ""

    # باقي الأدوار — فقط البراندات المرتبطة بشركتهم
    user_companies = frappe.db.sql_list("""
        SELECT DISTINCT company
        FROM `tabUser Permission`
        WHERE user = %s
          AND allow = 'Company'
    """, user)

    if not user_companies:
        return "1=0"  # لا يرى شيء

    companies_str = ", ".join(f"'{c}'" for c in user_companies)
    return f"`tabBrand`.`company` IN ({companies_str})"


def menu_item_query(user, doctype=None):
    """يُقيّد رؤية Menu Items بالبراندات المسموح بها للمستخدم"""
    if not user:
        user = frappe.session.user

    if "System Manager" in frappe.get_roles(user):
        return ""

    if "Group CEO" in frappe.get_roles(user):
        return ""

    # جلب البراندات المسموح بها عبر User Permissions
    allowed_brands = frappe.db.sql_list("""
        SELECT DISTINCT `for_value`
        FROM `tabUser Permission`
        WHERE user = %s
          AND allow = 'Brand'
    """, user)

    if not allowed_brands:
        return "1=0"

    brands_str = ", ".join(f"'{b}'" for b in allowed_brands)
    return f"`tabMenu Item`.`brand` IN ({brands_str})"


def table_order_query(user, doctype=None):
    """يُقيّد رؤية Table Orders بالبراندات المسموح بها"""
    if not user:
        user = frappe.session.user

    if "System Manager" in frappe.get_roles(user):
        return ""

    if "Group CEO" in frappe.get_roles(user):
        return ""

    # الكاشير يرى طلباته فقط
    if frappe.get_roles(user) == ["Cashier", "All", "Guest"]:
        return f"`tabTable Order`.`cashier` = '{user}'"

    allowed_brands = frappe.db.sql_list("""
        SELECT DISTINCT `for_value`
        FROM `tabUser Permission`
        WHERE user = %s
          AND allow = 'Brand'
    """, user)

    if not allowed_brands:
        return "1=0"

    brands_str = ", ".join(f"'{b}'" for b in allowed_brands)
    return f"`tabTable Order`.`brand` IN ({brands_str})"
