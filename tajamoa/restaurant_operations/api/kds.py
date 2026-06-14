"""
tajamoa/restaurant_operations/api/kds.py
Kitchen Display System — إدارة شاشة المطبخ
"""

import frappe
from frappe.utils import now_datetime, time_diff_in_seconds, get_datetime


# ─── Hook: عند تأكيد POS Invoice ────────────────────────────────────
def on_pos_submit(doc, method):
    """يُستدعى من hooks عند submit POS Invoice"""
    if not doc.get("tajamoa_table_order"):
        return
    try:
        order = frappe.get_doc("Table Order", doc.tajamoa_table_order)
        order.status = "Billed"
        order.closed_time = now_datetime()
        order.save(ignore_permissions=True)
    except Exception:
        pass


# ─── Hook: عند إلغاء POS Invoice ────────────────────────────────────
def on_pos_cancel(doc, method):
    """يُستدعى من hooks عند cancel POS Invoice"""
    if not doc.get("tajamoa_table_order"):
        return
    try:
        order = frappe.get_doc("Table Order", doc.tajamoa_table_order)
        if order.status == "Billed":
            order.status = "Served"
            order.save(ignore_permissions=True)
    except Exception:
        pass


# ─── Scheduled: تنظيف الطلبات المكتملة ─────────────────────────────
def cleanup_completed_orders():
    """
    تُشغَّل يومياً الساعة 2 صباحاً.
    تؤرشف الطلبات المغلقة منذ أكثر من 24 ساعة من شاشة KDS.
    """
    frappe.db.sql("""
        UPDATE `tabTable Order Item`
        SET kds_status = 'Served'
        WHERE kds_status = 'Ready'
          AND modified < NOW() - INTERVAL 24 HOUR
    """)
    frappe.db.commit()
    frappe.logger().info("KDS cleanup_completed_orders: done")


# ─── Scheduled: فحص الطلبات المتأخرة ────────────────────────────────
def check_delayed_orders():
    """
    تُشغَّل كل دقيقة.
    ترسل تنبيهاً Realtime للطلبات التي تجاوزت وقت التحضير.
    """
    try:
        delayed = frappe.db.sql("""
            SELECT
                toi.parent   AS order_name,
                toi.item_name_ar,
                toi.kitchen_station,
                toi.kds_status,
                tord.brand,
                tord.kitchen_sent_time
            FROM `tabTable Order Item` toi
            JOIN `tabTable Order` tord ON tord.name = toi.parent
            WHERE toi.kds_status IN ('Pending', 'In Progress')
              AND tord.kitchen_sent_time IS NOT NULL
              AND tord.kitchen_sent_time < NOW() - INTERVAL 20 MINUTE
              AND tord.status NOT IN ('Billed', 'Cancelled')
        """, as_dict=True)

        for row in delayed:
            frappe.publish_realtime(
                event="kds_delayed_alert",
                message={
                    "order":    row.order_name,
                    "item":     row.item_name_ar,
                    "station":  row.kitchen_station,
                    "since":    str(row.kitchen_sent_time),
                },
                room=f"kds_{row.brand}"
            )
    except Exception as e:
        frappe.logger().error(f"check_delayed_orders error: {e}")


# ─── API: تحديث حالة صنف في KDS ─────────────────────────────────────
@frappe.whitelist()
def update_item_status(order_name: str, item_idx: int, status: str):
    """
    يُستدعى من شاشة KDS عند تغيير حالة صنف.
    status: Pending | In Progress | Ready | Served
    """
    allowed = ("Pending", "In Progress", "Ready", "Served")
    if status not in allowed:
        frappe.throw(f"Invalid status. Allowed: {', '.join(allowed)}")

    order = frappe.get_doc("Table Order", order_name)
    item  = order.items[int(item_idx) - 1]
    item.kds_status = status
    order.save(ignore_permissions=True)

    # إذا كل الأصناف جاهزة → حدّث حالة الطلب
    all_ready = all(i.kds_status in ("Ready", "Served") for i in order.items)
    if all_ready and order.status == "In Preparation":
        order.status = "Ready"
        order.ready_time = now_datetime()
        order.save(ignore_permissions=True)

        frappe.publish_realtime(
            event="order_ready",
            message={"order": order_name, "brand": order.brand},
            room=f"brand_{order.brand}"
        )

    return {"status": status, "order_status": order.status}


# ─── API: جلب طلبات KDS النشطة ──────────────────────────────────────
@frappe.whitelist()
def get_active_orders(brand: str):
    """جلب كل الطلبات النشطة لعرضها على شاشة KDS"""
    orders = frappe.get_all(
        "Table Order",
        filters={
            "brand":  brand,
            "status": ["in", ["Sent to Kitchen", "In Preparation", "Ready"]],
        },
        fields=[
            "name", "status", "order_type", "dining_table",
            "kitchen_sent_time", "cover_count", "delivery_source",
        ],
        order_by="kitchen_sent_time asc"
    )

    for order in orders:
        order["items"] = frappe.get_all(
            "Table Order Item",
            filters={"parent": order.name},
            fields=[
                "item_name_ar", "qty", "modifiers_display",
                "item_notes", "kitchen_station", "kds_status", "idx"
            ],
            order_by="idx asc"
        )
        # حساب الوقت المنقضي بالدقائق
        if order.kitchen_sent_time:
            elapsed = time_diff_in_seconds(now_datetime(), order.kitchen_sent_time)
            order["elapsed_minutes"] = round(elapsed / 60, 1)
        else:
            order["elapsed_minutes"] = 0

    return orders
