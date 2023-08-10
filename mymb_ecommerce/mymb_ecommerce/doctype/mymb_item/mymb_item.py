# Copyright (c) 2023, Crowdechain S.r.o and contributors
# For license information, please see license.txt


from typing import Dict, Optional

import frappe
from erpnext import get_default_company
from frappe import _
from frappe.model.document import Document
from frappe.utils import cstr, get_datetime, now


class MymbItem(Document):
	erpnext_item_code: str  # item_code in ERPNext
	integration: str  # name of integration
	integration_item_code: str  # unique id of product on integration
	variant_id: str  # unique id of product variant on integration
	has_variants: int  # is the product a template, i.e. does it have varients
	variant_of: str  # template id of ERPNext item
	sku: str  # SKU

	def validate(self):
		self.set_defaults()

	def before_insert(self):
		self.check_unique_constraints()

	def check_unique_constraints(self) -> None:
		filters = []

		unique_integration_item_code = {
			"integration": self.integration,
			"erpnext_item_code": self.erpnext_item_code,
			"integration_item_code": self.integration_item_code,
		}

		if self.variant_id:
			unique_integration_item_code.update({"variant_id": self.variant_id})

		filters.append(unique_integration_item_code)

		if self.sku:
			unique_sku = {"integration": self.integration, "sku": self.sku}
			filters.append(unique_sku)

		for filter in filters:
			if frappe.db.exists("Mymb Item", filter):
				frappe.throw(_("Mymb Item already exists"), exc=frappe.DuplicateEntryError)

	def set_defaults(self):
		if not self.inventory_synced_on:
			# set to start of epoch time i.e. not synced
			self.inventory_synced_on = get_datetime("1970-01-01")


def is_synced(
	integration: str,
	integration_item_code: str,
	variant_id: Optional[str] = None,
	sku: Optional[str] = None,
) -> bool:
	"""Check if item is synced from integration.

	sku is optional. Use SKU alone with integration to check if it's synced.
	E.g.
	        integration: mymb b2c,
	        integration_item_code: TSHIRT
	"""

	if sku:
		return _is_sku_synced(integration, sku)

	filter = {"integration": integration, "integration_item_code": integration_item_code}

	if variant_id:
		filter.update({"variant_id": variant_id})

	return bool(frappe.db.exists("Mymb Item", filter))


def _is_sku_synced(integration: str, sku: str) -> bool:
	filter = {"integration": integration, "sku": sku}
	return bool(frappe.db.exists("Mymb Item", filter))


def get_erpnext_item_code(
	integration: str,
	integration_item_code: str,
	variant_id: Optional[str] = None,
	has_variants: Optional[int] = 0,
) -> Optional[str]:
	filters = {"integration": integration, "integration_item_code": integration_item_code}
	if variant_id:
		filters.update({"variant_id": variant_id})
	elif has_variants:
		filters.update({"has_variants": 1})

	return frappe.db.get_value("Mymb Item", filters, fieldname="erpnext_item_code")


def get_erpnext_item(
	integration: str,
	integration_item_code: str,
	variant_id: Optional[str] = None,
	sku: Optional[str] = None,
	has_variants: Optional[int] = 0,
):
	"""Get ERPNext item for specified mymb_item.

	Note: If variant_id is not specified then item is assumed to be single OR template.
	"""

	item_code = None
	if sku:
		item_code = frappe.db.get_value(
			"Mymb Item", {"sku": sku, "integration": integration}, fieldname="erpnext_item_code"
		)
	if not item_code:
		item_code = get_erpnext_item_code(
			integration, integration_item_code, variant_id=variant_id, has_variants=has_variants
		)

	if item_code:
		return frappe.get_doc("Item", item_code)


def create_or_update_mymb_item(
	integration: str,
	integration_item_code: str,
	item_dict: Dict,
	variant_id: Optional[str] = None,
	sku: Optional[str] = None,
	oarti: Optional[str] = None,
	variant_of: Optional[str] = None,
	has_variants=0,
	qty=0
) -> None:

	# SKU not allowed for template items
	sku = cstr(sku) if not has_variants else None

	if is_synced(integration, integration_item_code, variant_id, sku):
		return

	# Check if the item already exists by a unique identifier, such as SKU
	existing_item = frappe.db.get_value("Item", {"name": sku}) if sku else None

	# Update existing item if found
	if existing_item:
		item = frappe.get_doc("Item", existing_item)
		item.update(item_dict)
		item.flags.from_integration = True
		item.save(ignore_permissions=True)
	else:
		# Create a new item if not found
		item_data = {
			"doctype": "Item",
			"is_stock_item": 1,
			"is_sales_item": 1,
			"include_item_in_manufacturing": 0,
			"item_defaults": [{"company": get_default_company()}],
		}
		if qty > 0:
			item_dict['disabled'] =  0  # Enabme the item
		item_data.update(item_dict)  # Updating the item_data with the values from item_dict
		new_item = frappe.get_doc(item_data)
		new_item.flags.from_integration = True
		new_item.insert(ignore_permissions=True)
		create_stock_entry(new_item, qty)  # U

	# Create or update the corresponding Mymb Item doctype
	mymb_item_data = {
		"doctype": "Mymb Item",
		"integration": integration,
		"erpnext_item_code": existing_item or new_item.name,
		"integration_item_code": integration_item_code,
		"has_variants": has_variants,
		"variant_id": cstr(variant_id),
		"variant_of": cstr(variant_of),
		"sku": sku,
		"oarti": oarti,
		"item_synced_on": now(),
	}

	# Check if the Mymb Item already exists
	existing_mymb_item = frappe.db.get_value("Mymb Item", {"integration_item_code": integration_item_code , "integration": integration})

	if existing_mymb_item:
		mymb_item = frappe.get_doc("Mymb Item", existing_mymb_item)
		mymb_item.update(mymb_item_data)
		mymb_item.save(ignore_permissions=True)
	else:
		mymb_item = frappe.get_doc(mymb_item_data)
		mymb_item.insert(ignore_permissions=True)


def create_stock_entry(item, qty):
    warehouse = frappe.db.get_single_value('Stock Settings', 'default_warehouse')
    
    stock_entry = frappe.get_doc({
        "doctype": "Stock Entry",
        "purpose": "Material Receipt", # Or another purpose depending on your use case
        "stock_entry_type": "Material Receipt", # This may vary based on your requirements
        "from_warehouse": "", # May not be required if this is an initial receipt
        "to_warehouse": warehouse, # The warehouse where the stock will be received
        "items": [
            {
                "item_code": item.get("item_code"),
                "qty": qty, # Add the quantity of items
                "uom": item.get("uom"), # Add the unit of measure
                "t_warehouse": warehouse # The target warehouse for this item
            }
        ]
    })

    stock_entry.insert(ignore_permissions=True)
    stock_entry.submit()
    frappe.db.commit() # Commit the transaction to ensure it's saved
