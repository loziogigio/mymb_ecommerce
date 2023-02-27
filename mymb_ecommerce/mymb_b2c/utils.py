import datetime

import frappe

from mymb_ecommerce.mymb_ecommerce.doctype.mymb_ecommerce_log.mymb_ecommerce_log import (
	create_log,
)
from mymb_ecommerce.mymb_b2c.constants import MODULE_NAME

SYNC_METHODS = {
	"Items": "ecommerce_integrations.mymb_b2c.product.upload_new_items",
	"Orders": "ecommerce_integrations.mymb_b2c.order.sync_new_orders",
	"Inventory": "ecommerce_integrations.mymb_b2c.inventory.update_inventory_on_mymb_b2c",
}

DOCUMENT_URL_FORMAT = {
	"Sales Order": "https://{site}/order/orderitems?orderCode={code}",
	"Sales Invoice": "https://{site}/order/orderitems?orderCode={code}",
	"Item": "https://{site}/products/edit?sku={code}",
	"Unicommerce Shipment Manifest": "https://{site}/manifests/edit?code={code}",
	"Stock Entry": "https://{site}/grns",
}


def create_mymb_b2c_log(**kwargs):
	return create_log(module_def=MODULE_NAME, **kwargs)


@frappe.whitelist()
def get_mymb_b2c_document_url(code: str, doctype: str) -> str:
	if not isinstance(code, str):
		frappe.throw(frappe._("Invalid Document code"))

	site = frappe.db.get_single_value("Unicommerce Settings", "mymb_b2c_site", cache=True)
	url = DOCUMENT_URL_FORMAT.get(doctype, "")

	return url.format(site=site, code=code)


@frappe.whitelist()
def force_sync(document) -> None:
	frappe.only_for("System Manager")

	method = SYNC_METHODS.get(document)
	if not method:
		frappe.throw(frappe._("Unknown method"))
	frappe.enqueue(method, queue="long", is_async=True, **{"force": True})


def get_mymb_b2c_date(timestamp: int) -> datetime.date:
	""" Convert mymb_b2c ms timestamp to datetime."""
	return datetime.date.fromtimestamp(timestamp // 1000)


def remove_non_alphanumeric_chars(filename: str) -> str:
	return "".join(c for c in filename if c.isalpha() or c.isdigit()).strip()
