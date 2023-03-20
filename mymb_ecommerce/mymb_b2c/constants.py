# Copyright (c) 2021, Frappe and contributors
# For license information, please see LICENSE
import re

MODULE_NAME = "mymb b2c"
SETTINGS_DOCTYPE = "Mymb b2c Settings"
SETTING_DOCTYPE = "Mymb b2c Settings"
OLD_SETTINGS_DOCTYPE = "Mymb b2c Settings"

API_VERSION = "2022-04"

WEBHOOK_EVENTS = [
	"orders/create",
	"orders/paid",
	"orders/fulfilled",
	"orders/cancelled",
	"orders/partially_fulfilled",
]

EVENT_MAPPER = {
	"orders/create": "ecommerce_integrations.mymb_b2c.order.sync_sales_order",
	"orders/paid": "ecommerce_integrations.mymb_b2c.invoice.prepare_sales_invoice",
	"orders/fulfilled": "ecommerce_integrations.mymb_b2c.fulfillment.prepare_delivery_note",
	"orders/cancelled": "ecommerce_integrations.mymb_b2c.order.cancel_order",
	"orders/partially_fulfilled": "ecommerce_integrations.mymb_b2c.fulfillment.prepare_delivery_note",
}

SHOPIFY_VARIANTS_ATTR_LIST = ["option1", "option2", "option3"]

# custom fields

CUSTOMER_ID_FIELD = "mymb_b2c_customer_id"
ORDER_ID_FIELD = "mymb_b2c_order_id"
ORDER_NUMBER_FIELD = "mymb_b2c_order_number"
ORDER_STATUS_FIELD = "mymb_b2c_order_status"
FULLFILLMENT_ID_FIELD = "mymb_b2c_fulfillment_id"
SUPPLIER_ID_FIELD = "mymb_b2c_supplier_id"
ADDRESS_ID_FIELD = "mymb_b2c_address_id"
ORDER_ITEM_DISCOUNT_FIELD = "mymb_b2c_item_discount"
ITEM_SELLING_RATE_FIELD = "mymb_b2c_selling_rate"

# ERPNext already defines the default UOMs from Shopify but names are different
WEIGHT_TO_ERPNEXT_UOM_MAP = {"kg": "Kg", "g": "Gram", "oz": "Ounce", "lb": "Pound"}


DEFAULT_WEIGHT_UOM = "Kg"
MYMB_B2C_SKU_PATTERN = re.compile(r"[A-Za-z0-9._\-/]{3,45}")


# Custom fields
ITEM_SYNC_CHECKBOX = "sync_with_mymb_b2c"
ORDER_CODE_FIELD = "mymb_b2c_order_code"
CHANNEL_ID_FIELD = "mymb_b2c_channel_id"
ORDER_STATUS_FIELD = "mymb_b2c_order_status"
ORDER_INVOICE_STATUS_FIELD = "mymb_b2c_invoicing_status"
ORDER_ITEM_CODE_FIELD = "mymb_b2c_order_item_code"
ORDER_ITEM_BATCH_NO = "mymb_b2c_batch_code"
PRODUCT_CATEGORY_FIELD = "mymb b2c product category"
FACILITY_CODE_FIELD = "mymb_b2c_facility_code"
INVOICE_CODE_FIELD = "mymb_b2c_invoice_code"
SHIPPING_PACKAGE_CODE_FIELD = "mymb_b2c_shipping_package_code"
RETURN_CODE_FIELD = "mymb_b2c_return_code"
TRACKING_CODE_FIELD = "mymb_b2c_tracking_code"
SHIPPING_PROVIDER_CODE = "mymb_b2c_shipping_provider"
MANIFEST_GENERATED_CHECK = "mymb_b2c_manifest_generated"
ADDRESS_JSON_FIELD = "mymb_b2c_raw_billing_address"
CUSTOMER_CODE_FIELD = "mymb_b2c_customer_code"
PACKAGE_TYPE_FIELD = "mymb_b2c_package_type"
ITEM_LENGTH_FIELD = "mymb_b2c_item_length"
ITEM_WIDTH_FIELD = "mymb_b2c_item_width"
ITEM_HEIGHT_FIELD = "mymb_b2c_item_height"
ITEM_BATCH_GROUP_FIELD = "mymb_b2c_batch_group_code"
SHIPPING_PACKAGE_STATUS_FIELD = "mymb_b2c_shipping_package_status"
IS_COD_CHECKBOX = "mymb_b2c_is_cod"
SHIPPING_METHOD_FIELD = "mymb_b2c_shipping_method"
