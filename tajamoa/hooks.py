app_name = "tajamoa"
app_title = "Tajamoa Group ERP"
app_publisher = "Tajamoa Group"
app_description = "Multi-Brand Restaurant & Cloud Kitchen ERP"
app_email = "erp@tajamoa.com"
app_license = "MIT"
app_version = "1.0.0"

# ─── Modules ────────────────────────────────────────────────────
required_apps = ["frappe", "erpnext"]

# ─── Webhook Routes ─────────────────────────────────────────────
website_route_rules = [
    {
        "from_route": "/api/jareb/webhook",
        "to_route": "tajamoa.restaurant_operations.api.jareb_webhook.receive",
    },
    {
        "from_route": "/api/menu/sync/<brand_code>",
        "to_route": "tajamoa.restaurant_operations.api.menu_sync.push_menu",
    },
]

# ─── Fixtures (exported with bench export-fixtures) ─────────────
fixtures = [
    "Custom Field",
    "Property Setter",
    "Print Format",
    "Role",
    "Notification",
    "Workflow",
    "Workflow State",
    "Workflow Action Master",
    {"dt": "Workspace", "filters": [["module", "=", "Restaurant Operations"]]},
    {"dt": "Report", "filters": [["module", "=", "Restaurant Operations"]]},
]

# ─── Install / Uninstall Hooks ───────────────────────────────────
after_install = "tajamoa.setup.install.after_install"
after_migrate = "tajamoa.setup.install.after_migrate"

# ─── Document Events ─────────────────────────────────────────────
doc_events = {
    # عند تأكيد فاتورة POS — تحديث KDS
    "POS Invoice": {
        "on_submit": "tajamoa.restaurant_operations.api.kds.on_pos_submit",
        "on_cancel": "tajamoa.restaurant_operations.api.kds.on_pos_cancel",
    },
    # عند استقبال طلب توصيل من جرب تك
    "Sales Order": {
        "after_insert": "tajamoa.restaurant_operations.api.jareb_webhook.on_order_created",
    },
}

# ─── Scheduled Tasks ─────────────────────────────────────────────
scheduler_events = {
    "cron": {
        # مزامنة المنيو مع جرب تك كل ساعة
        "0 * * * *": [
            "tajamoa.restaurant_operations.api.menu_sync.auto_sync_all_brands"
        ],
        # تقرير مبيعات يومي الساعة 6:00 صباحاً
        "0 6 * * *": [
            "tajamoa.restaurant_operations.report.daily_summary.send_report"
        ],
        # تنظيف طلبات KDS المكتملة كل 24 ساعة
        "0 2 * * *": [
            "tajamoa.restaurant_operations.api.kds.cleanup_completed_orders"
        ],
    },
    "all": [
        # فحص الطلبات المتأخرة في KDS كل دقيقة
        "tajamoa.restaurant_operations.api.kds.check_delayed_orders"
    ],
}

# ─── Jinja Custom Functions ──────────────────────────────────────
jinja = {
    "methods": [
        "tajamoa.restaurant_operations.utils.get_brand_logo",
        "tajamoa.restaurant_operations.utils.format_order_items",
    ]
}

# ─── Permission Query Conditions (Row-level Security) ────────────
permission_query_conditions = {
    "Brand": "tajamoa.restaurant_operations.permissions.brand_query",
    "Menu Item": "tajamoa.restaurant_operations.permissions.menu_item_query",
    "Table Order": "tajamoa.restaurant_operations.permissions.table_order_query",
}

# ─── Override Standard Methods ────────────────────────────────────
override_whitelisted_methods = {
    # تخصيص طريقة إرجاع فاتورة POS لدعم الـ modifiers
    "erpnext.accounts.doctype.pos_invoice.pos_invoice.make_return_doc": (
        "tajamoa.restaurant_operations.overrides.pos_invoice.make_return_doc"
    ),
}
