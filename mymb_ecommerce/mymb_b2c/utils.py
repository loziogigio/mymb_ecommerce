# Copyright (c) 2021, Frappe and contributors
# For license information, please see LICENSE
from typing import List

import frappe
from frappe import _, _dict

from mymb_ecommerce.mymb_ecommerce.doctype.mymb_ecommerce_log.mymb_ecommerce_log import (
	create_log,
)
from mymb_ecommerce.mymb_b2c.constants import (
	MODULE_NAME,
	SETTING_DOCTYPE,
)


def create_mymb_b2c_log(**kwargs):
	return create_log(module_def=MODULE_NAME, **kwargs)


def migrate_from_old_connector(payload=None, request_id=None):
	"""This function is called to migrate data from old connector to new connector."""

	if request_id:
		log = frappe.get_doc("Mymb Ecommerce Log", request_id)
	else:
		log = create_mymb_b2c_log(
			status="Queued", method="mymb_ecommerce.mymb_b2c.utils.migrate_from_old_connector",
		)

	frappe.enqueue(
		method=_migrate_items_to_ecommerce_item, queue="long", is_async=True, log=log,
	)


def _migrate_items_to_ecommerce_item(log):

	mymb_b2c_fields = ["mymb_b2c_product_id", "mymb_b2c_variant_id"]

	for field in mymb_b2c_fields:
		if not frappe.db.exists({"doctype": "Custom Field", "fieldname": field}):
			return

	items = _get_items_to_migrate()

	try:
		_create_ecommerce_items(items)
	except Exception:
		log.status = "Error"
		log.traceback = frappe.get_traceback()
		log.save()
		return

	frappe.db.set_value(SETTING_DOCTYPE, SETTING_DOCTYPE, "is_old_data_migrated", 1)
	log.status = "Success"
	log.save()


def _get_items_to_migrate() -> List[_dict]:
	"""get all list of items that have mymb_b2c fields but do not have associated ecommerce item."""

	old_data = frappe.db.sql(
		"""SELECT item.name as erpnext_item_code, mymb_b2c_product_id, mymb_b2c_variant_id, item.variant_of, item.has_variants
			FROM tabItem item
			LEFT JOIN `tabMymb Item` ei on ei.erpnext_item_code = item.name
			WHERE ei.erpnext_item_code IS NULL AND mymb_b2c_product_id IS NOT NULL""",
		as_dict=True,
	)

	return old_data or []


def _create_ecommerce_items(items: List[_dict]) -> None:
	for item in items:
		if not all((item.erpnext_item_code, item.mymb_b2c_product_id, item.mymb_b2c_variant_id)):
			continue

		ecommerce_item = frappe.get_doc(
			{
				"doctype": "Mymb Item",
				"integration": MODULE_NAME,
				"erpnext_item_code": item.erpnext_item_code,
				"integration_item_code": item.mymb_b2c_product_id,
				"variant_id": item.mymb_b2c_variant_id,
				"variant_of": item.variant_of,
				"has_variants": item.has_variants,
			}
		)
		ecommerce_item.save()
