from . import __version__ as app_version

app_name = "mymb_ecommerce"
app_title = "Mymb Ecommerce"
app_publisher = "Crowdechain S.r.o"
app_description = "Mymb Ecommerce integrations"
app_email = "developers@crowdechain.com"
app_license = "MIT"

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/ecommerce_integrations/css/mymb_ecommerce.css"
# Include js files in header of desk.html
app_include_js = [
     "/assets/mymb_ecommerce/js/papaparse.min.5.3.0.js",
    # Add other JS files if needed
]
# app_include_js = "/assets/ecommerce_integrations/js/mymb_ecommerce.js"

# include js, css files in header of web template
# web_include_css = "/assets/ecommerce_integrations/css/mymb_ecommerce.css"
# web_include_js = "/assets/ecommerce_integrations/js/mymb_ecommerce.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "ecommerce_integrations/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Installation
# ------------

# before_install = "mymb_ecommerce.install.before_install"
# after_install = "mymb_ecommerce.install.after_install"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "mymb_ecommerce.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
# 	"ToDo": "custom_app.overrides.CustomToDo"
# }

# Document Events
# ---------------
# Hook on document methods and events

doc_events = {
	"Item": {
		# "after_insert": "mymb_ecommerce.mymb_b2c.product.upload_erpnext_item",
		# "on_update": "mymb_ecommerce.mymb_b2c.product.upload_erpnext_item",
		"validate": [
			"mymb_ecommerce.utils.taxation.validate_tax_template",
			# "mymb_ecommerce.unicommerce.product.validate_item",
		],
	},
	"Sales Order": {
		# "on_update_after_submit": "mymb_ecommerce.unicommerce.order.update_shipping_info",
		# "on_cancel": "mymb_ecommerce.unicommerce.status_updater.ignore_pick_list_on_sales_order_cancel",
	},
	# "Stock Entry": {
	# 	"validate": "mymb_ecommerce.unicommerce.grn.validate_stock_entry_for_grn",
	# 	"on_submit": "mymb_ecommerce.unicommerce.grn.upload_grn",
	# 	"on_cancel": "mymb_ecommerce.unicommerce.grn.prevent_grn_cancel",
	# },
	"Item Price": {"on_change": "mymb_ecommerce.utils.price_list.discard_item_prices"},
}

# Scheduled Tasks
# ---------------

scheduler_events = {
	# "all": ["mymb_ecommerce.mymb_b2c.inventory.update_inventory_on_shopify"],
	"daily": [],
	"daily_long": [
		# "mymb_ecommerce.zenoti.doctype.zenoti_settings.zenoti_settings.sync_stocks"
	],
	"hourly": [
		# "mymb_ecommerce.mymb_b2c.order.sync_old_orders",
		# "mymb_ecommerce.amazon.doctype.amazon_sp_api_settings.amazon_sp_api_settings.schedule_get_order_details",
	],
	"hourly_long": [
		# "mymb_ecommerce.zenoti.doctype.zenoti_settings.zenoti_settings.sync_invoices",
		# "mymb_ecommerce.unicommerce.product.upload_new_items",
		# "mymb_ecommerce.unicommerce.status_updater.update_sales_order_status",
		# "mymb_ecommerce.unicommerce.status_updater.update_shipping_package_status",
	],
	"weekly": [],
	"monthly": [],
	"cron": {
		# Every five minutes
		# "*/5 * * * *": [
		# 	# "mymb_ecommerce.unicommerce.order.sync_new_orders",
		# 	# "mymb_ecommerce.unicommerce.inventory.update_inventory_on_unicommerce",
		# ],
	},
}


# bootinfo - hide old doctypes
# extend_bootinfo = "mymb_ecommerce.boot.boot_session"

# Testing
# -------

before_tests = "mymb_ecommerce.utils.before_test.before_tests"

# Overriding Methods
# ------------------------------
#
override_whitelisted_methods = {
	"payments.payment_gateways.doctype.paypal_settings.paypal_settings.get_express_checkout_details": "mymb_ecommerce.mymb_ecommerce.payment.get_express_checkout_details",
    "payments.payment_gateways.doctype.paypal_settings.paypal_settings.confirm_payment": "mymb_ecommerce.mymb_ecommerce.payment.confirm_payment"
}
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "mymb_ecommerce.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]


# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

