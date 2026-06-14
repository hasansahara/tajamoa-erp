"""
tajamoa/restaurant_operations/report/daily_summary/daily_summary.py
تقرير المبيعات اليومي — يُرسل كل صباح الساعة 6:00
"""

import frappe
from frappe.utils import today, add_days, nowdate


def send_report():
    """
    Scheduled: تُشغَّل يومياً الساعة 6:00 صباحاً.
    تجمع مبيعات الأمس لكل براند وترسل ملخصاً بالإيميل.
    """
    report_date = add_days(today(), -1)   # أمس
    data        = get_daily_summary(report_date)

    if not data:
        frappe.logger().info(f"daily_summary: no data for {report_date}")
        return

    # جلب المستلمين من الإعدادات
    settings   = frappe.get_single("Tajamoa Settings")
    recipients = (settings.get("daily_report_emails") or "").split(",")
    recipients = [r.strip() for r in recipients if r.strip()]

    if not recipients:
        frappe.logger().warning("daily_summary: no recipients configured")
        return

    # بناء جسم الإيميل
    rows = "".join(
        f"<tr>"
        f"<td>{r['brand']}</td>"
        f"<td>{r['order_count']}</td>"
        f"<td>{r['total_qty']}</td>"
        f"<td style='text-align:right'>{r['gross_sales']:,.2f} SAR</td>"
        f"<td style='text-align:right'>{r['discount']:,.2f} SAR</td>"
        f"<td style='text-align:right'><b>{r['net_sales']:,.2f} SAR</b></td>"
        f"</tr>"
        for r in data
    )
    grand_net = sum(r["net_sales"] for r in data)

    html = f"""
    <div dir="rtl" style="font-family:Arial; font-size:14px;">
      <h2>ملخص المبيعات اليومي — {report_date}</h2>
      <table border="1" cellpadding="6" cellspacing="0" style="border-collapse:collapse; width:100%">
        <thead style="background:#1D3557; color:#fff;">
          <tr>
            <th>البراند</th>
            <th>عدد الطلبات</th>
            <th>الكميات</th>
            <th>المبيعات الإجمالية</th>
            <th>الخصومات</th>
            <th>صافي المبيعات</th>
          </tr>
        </thead>
        <tbody>{rows}</tbody>
        <tfoot style="background:#f0f0f0; font-weight:bold;">
          <tr>
            <td colspan="5">الإجمالي</td>
            <td style="text-align:right">{grand_net:,.2f} SAR</td>
          </tr>
        </tfoot>
      </table>
      <br/>
      <small style="color:#888">أُرسل تلقائياً من نظام تجمعة ERP</small>
    </div>
    """

    frappe.sendmail(
        recipients=recipients,
        subject=f"[تجمعة] ملخص المبيعات — {report_date}",
        message=html,
        delayed=False,
    )
    frappe.logger().info(f"daily_summary: sent for {report_date} to {recipients}")


def get_daily_summary(report_date: str) -> list:
    """
    جلب ملخص المبيعات من POS Invoices.
    يمكن استدعاؤها مباشرة من واجهة ERPNext أيضاً.
    """
    return frappe.db.sql("""
        SELECT
            pi.tajamoa_brand                            AS brand,
            COUNT(DISTINCT pi.name)                     AS order_count,
            SUM(pii.qty)                                AS total_qty,
            SUM(pii.amount)                             AS gross_sales,
            COALESCE(SUM(pi.discount_amount), 0)        AS discount,
            SUM(pii.amount) - COALESCE(SUM(pi.discount_amount), 0) AS net_sales
        FROM `tabPOS Invoice` pi
        JOIN `tabPOS Invoice Item` pii ON pii.parent = pi.name
        WHERE pi.docstatus = 1
          AND pi.posting_date = %(date)s
          AND pi.tajamoa_brand IS NOT NULL
          AND pi.tajamoa_brand != ''
        GROUP BY pi.tajamoa_brand
        ORDER BY net_sales DESC
    """, {"date": report_date}, as_dict=True)
