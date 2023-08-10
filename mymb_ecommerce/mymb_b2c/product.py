from typing import List, NewType
from frappe.utils.data import nowtime, today
from mymb_ecommerce.mymb_b2c.settings.configurations import Configurations
from mymb_ecommerce.utils.Media import Media

from mymb_ecommerce.mymb_b2c.api_product import MymbB2cItem

import frappe
from frappe import _
from frappe.utils import get_url, now
from frappe.utils.nestedset import get_root_of
from stdnum.ean import is_valid as validate_barcode
from typing import Any


from multiprocessing import Pool

from mymb_ecommerce.mymb_ecommerce.doctype.mymb_item import mymb_item
from mymb_ecommerce.mymb_b2c.api_client import JsonDict, MymbAPIClient
from mymb_ecommerce.mymb_b2c.constants import (
	DEFAULT_WEIGHT_UOM,
	ITEM_BATCH_GROUP_FIELD,
	ITEM_HEIGHT_FIELD,
	ITEM_LENGTH_FIELD,
	ITEM_SYNC_CHECKBOX,
	ITEM_WIDTH_FIELD,
	MODULE_NAME,
	PRODUCT_CATEGORY_FIELD,
	SETTINGS_DOCTYPE,
	MYMB_B2C_SKU_PATTERN,
)
from mymb_ecommerce.mymb_b2c.utils import create_mymb_b2c_log

ItemCode = NewType("ItemCode", str)

# mymb_b2c product to ERPNext item mapping
# reference: https://documentation.mymb_b2c.com/docs/itemtype-get.html
MYMB_B2C_TO_ERPNEXT_ITEM_MAPPING = {
    "sku": "item_code",
    "name": "item_name",
    "description": "description",
    "net_price_with_vat": "standard_rate",
    "slug": "website_link",
    "brand": "brand"
}


ERPNEXT_TO_MYMB_B2C_ITEM_MAPPING = {v: k for k, v in MYMB_B2C_TO_ERPNEXT_ITEM_MAPPING.items()}

@frappe.whitelist(allow_guest=True, methods=['POST'])
def import_all_products_from_mymb_b2c(batch_size: int = 100) -> str:
    """Import all products from Mymb b2c to ERPNext using background jobs"""
    # Initialize MymbB2cItem client
    client = MymbB2cItem()

    # Get total count of items
    total_count = client.get_mymb_b2c_item_count()
    total_count = 50


    # Process items in batches
    for offset in range(0, total_count, batch_size):
        # Get batch of items
        print(offset,total_count, batch_size)
        items = client.get_item_batch_by_offset(batch_size=batch_size, offset=offset)

        # Submit jobs to queue
        for item in items:
             frappe.enqueue(import_mymb_b2c_single_product, mymb_b2c_item=item , queue='short')

    return "Importing products from Mymb b2c is in progress"

@frappe.whitelist(allow_guest=True, methods=['POST'])
def import_mymb_b2c_multiple_products(sku_array: list = None):
    # Check if SKU array is provided
    if sku_array:
        # Loop through each SKU in the array
        for sku in sku_array:
            # Process each SKU
            import_mymb_b2c_single_product(sku)



@frappe.whitelist(allow_guest=True, methods=['POST'])
def import_mymb_b2c_single_product(sku: str = None , mymb_b2c_item: any = None):
    
    if mymb_b2c_item is not None:
        item = mymb_b2c_item
    elif sku is not None:
        client = MymbB2cItem()
        item = client.get_mymb_b2c_item(sku)
    else:
        return "No SKU or mymb_b2c_item provided"

    try:
        import_product_from_mymb_b2c(item, sku) # Pass SKU here
        update_main_image_item(item)
    except Exception as e:
        # Log the error
        frappe.log_error(message=frappe.get_traceback(), title="Error while importing mymb_b2c item")
        return f"Import failed due to error: {str(e)}"
        

    return "Import successful"


def stock_reconciliation_b2c_product(sku , stock):
		
		item = frappe.get_doc('Item', sku)
		item.disabled = 0
		item.save()
		

		# Update stock
		warehouse = frappe.db.get_single_value('Stock Settings', 'default_warehouse')

		# Get current stock qty in the warehouse
		current_qty = frappe.db.get_value('Bin', {'item_code': sku, 'warehouse': warehouse}, 'actual_qty')

		# Calculate the new qty to add to the warehouse
		new_qty = stock

		if current_qty != new_qty:
			# Create a dictionary with the item data
			item_data = get_item_data(warehouse=warehouse,row=item, qty=new_qty, current_qty=current_qty, valuation_rate=item.standard_rate)

			# Create a stock reconciliation for the item
			stock_recon = frappe.get_doc({
				'doctype': 'Stock Reconciliation',
				'title': f"Stock Update for {item.name}",
				'purpose': 'Stock Reconciliation',
				'warehouse': warehouse,
				'items': [item_data]
			})
			stock_recon.insert(ignore_permissions=True)
			stock_recon.submit()

def update_main_image_item(mymb_b2c_item):
	item = mymb_b2c_item
	item_code = item["sku"]
	item = frappe.get_doc('Item', item_code)
	if(mymb_b2c_item["images"]):
		config = Configurations()
		image_uri_instance = config.get_image_uri_instance()
		media = Media(image_uri_instance)
		images = media.get_image_sizes(mymb_b2c_item)
		if item.image != images["gallery_pictures"][0]["url"]:
			item.image = images["gallery_pictures"][0]["url"]
			item.save(ignore_permissions=True)

def get_item_data(warehouse,row, qty, valuation_rate, current_qty, serial_no=None):
	return {
		"item_code": row.item_code,
		"warehouse": warehouse,
		"qty": qty,
		"item_name": row.item_name,
		"valuation_rate": valuation_rate,
		"current_qty": current_qty,
		"current_valuation_rate": valuation_rate
	}


def import_product_from_mymb_b2c(item: any , sku=None) -> None:
    """Sync specified SKU from Mymb b2c."""

    try:
        if not item:
            frappe.throw(_("Mymb b2c item not found"))
        if not sku:
            raise ValueError("SKU not found in item data")

        _check_and_match_existing_item(item)
		
        item_dict = _create_item_dict(item)
        mymb_item.create_or_update_mymb_item(MODULE_NAME, integration_item_code=sku, sku=sku, oarti=item["id"], item_dict=item_dict , qty=item.get("availability", 0) )

    except Exception as e:
        create_mymb_b2c_log(
            status="Failure",
            message=f"Failed to import Item: {sku} from Mymb b2c" if sku else "Failed to import Item from Mymb b2c",
            response_data=item,
            make_new=True,
            exception=e,
            rollback=True,
        )
        raise e  # This will re-raise the current exception. Be cautious where you catch this.
    else:
        create_mymb_b2c_log(
            status="Success",
            message=f"Successfully imported Item: {sku} from Mymb b2c",
            response_data=item,
            make_new=True,
        )



def _create_item_dict(mymb_b2c_item):
	""" Helper function to build item document fields"""

	item_dict = {"weight_uom": DEFAULT_WEIGHT_UOM}

	_validate_create_brand(mymb_b2c_item.get("brand"))

	for mymb_b2c_item_field, erpnext_field in MYMB_B2C_TO_ERPNEXT_ITEM_MAPPING.items():

		value = mymb_b2c_item.get(mymb_b2c_item_field)
		if not _validate_field(erpnext_field, value):
			continue

		item_dict[erpnext_field] = value

	item_dict["barcodes"] = _get_barcode_data(mymb_b2c_item)
	item_dict["disabled"] = int(not mymb_b2c_item.get("enabled"))
	item_dict["item_group"] = _get_item_group(mymb_b2c_item.get("categoryCode"))
	item_dict["name"] = mymb_b2c_item["sku"]  # when naming is by item series

	#If i have images in the image array i am taking the gallery version
	if(mymb_b2c_item["images"]):
		config = Configurations()
		image_uri_instance = config.get_image_uri_instance()
		media = Media(image_uri_instance)
		images = media.get_image_sizes(mymb_b2c_item)
		item_dict["image"] = images["gallery_pictures"][0]["url"]
		
	return item_dict


def _get_barcode_data(mymb_b2c_item):
	"""Extract barcode information from Mymb b2c item and return as child doctype row for Item table"""
	barcodes = []

	ean = mymb_b2c_item.get("ean")
	upc = mymb_b2c_item.get("upc")

	if ean and validate_barcode(ean):
		barcodes.append({"barcode": ean, "barcode_type": "EAN"})
	if upc and validate_barcode(upc):
		barcodes.append({"barcode": upc, "barcode_type": "UPC-A"})

	return barcodes


def _check_and_match_existing_item(mymb_b2c_item):
    """Tries to match new item with existing item using SKU == item_code.

    Returns true if matched and linked.
    """

    sku = mymb_b2c_item["sku"]
    id = mymb_b2c_item["id"]

    # Include integration module in the filter
    item_filter = {"integration_item_code": sku, "integration": MODULE_NAME}
    mymb_item_name = frappe.db.get_value("Mymb Item", item_filter)

    if mymb_item_name:
        # Update existing Mymb Item
        return True
    else:
        # Insert new Mymb Item
        item_name = frappe.db.get_value("Item", {"item_code": sku})
        if item_name:
            try:
                mymb_item = frappe.get_doc(
                    {
                        "doctype": "Mymb Item",
                        "integration": MODULE_NAME,
                        "erpnext_item_code": item_name,
                        "integration_item_code": sku,
                        "has_variants": 0,
                        "sku": sku,
                        "oarti": id
                    }
                )
                mymb_item.insert(ignore_permissions=True)
                return True
            except Exception as e:
                return f"Import failed due to error: {str(e)}"

    return False


def _validate_create_brand(brand):
	"""Create the brand if it does not exist."""
	if not brand:
		return

	if not frappe.db.exists("Brand", brand):
		frappe.get_doc(doctype="Brand", brand=brand).insert(ignore_permissions=True)


def _validate_field(item_field, name):
	"""Check if field exists in item doctype, if it's a link field then also check if linked document exists"""
	meta = frappe.get_meta("Item")
	field = meta.get_field(item_field)
	if not field:
		return False

	if field.fieldtype != "Link":
		return True

	doctype = field.options
	return bool(frappe.db.exists(doctype, name))


def _get_item_group(category_code):
	"""Given mymb_b2c category code find the Item group in ERPNext.

	Returns item group with following priority:
	        1. Item group that has mymb_b2c_product_code linked.
	        2. Default Item group configured in Mymb b2c settings.
	        3. root of Item Group tree."""

	# item_group = frappe.db.get_value("Item Group", {PRODUCT_CATEGORY_FIELD: category_code})
	# if category_code and item_group:
	# 	return item_group

	default_item_group = frappe.db.get_single_value("Mymb b2c Settings", "default_item_group")
	if default_item_group:
		return default_item_group

	return get_root_of("Item Group")


def upload_new_items(force=False) -> None:
	"""Upload new items to Mymb b2c on hourly basis.

	All the items that have "sync_with_mymb_b2c" checked but do not have
	corresponding Mymb Item, are pushed to Mymb b2c."""

	settings = frappe.get_cached_doc(SETTINGS_DOCTYPE)

	if not (settings.is_enabled() and settings.upload_item_to_mymb_b2c):
		return

	new_items = _get_new_items()
	if not new_items:
		return

	log = create_mymb_b2c_log(status="Queued", message="Item sync initiated", make_new=True)
	synced_items = upload_items_to_mymb_b2c(new_items)

	unsynced_items = set(new_items) - set(synced_items)

	log.message = (
		"Item sync completed\n"
		f"Synced items: {', '.join(synced_items)}\n"
		f"Unsynced items: {', '.join(unsynced_items)}"
	)
	log.status = "Success"
	log.save()


def _get_new_items() -> List[ItemCode]:
	new_items = frappe.db.sql(
		f"""
			SELECT item.item_code
			FROM tabItem item
			LEFT JOIN `tabMymb Item` ei
				ON ei.erpnext_item_code = item.item_code
				WHERE ei.erpnext_item_code is NULL
					AND item.{ITEM_SYNC_CHECKBOX} = 1
		"""
	)

	return [item[0] for item in new_items]


def upload_items_to_mymb_b2c(
	item_codes: List[ItemCode], client: MymbAPIClient = None
) -> List[ItemCode]:
	"""Upload multiple items to Mymb b2c.

	Return Successfully synced item codes.
	"""
	if not client:
		client = MymbAPIClient()

	synced_items = []

	for item_code in item_codes:
		item_data = _build_mymb_b2c_item(item_code)
		sku = item_data.get("skuCode")

		item_exists = bool(client.get_mymb_b2c_item(sku, log_error=False))
		_, status = client.create_update_item(item_data, update=item_exists)

		if status:
			_handle_mymb_item(item_code)
			synced_items.append(item_code)

	return synced_items


def _build_mymb_b2c_item(item_code: ItemCode) -> JsonDict:
	"""Build Mymb b2c item JSON using an ERPNext item"""
	item = frappe.get_doc("Item", item_code)

	item_json = {}

	for erpnext_field, uni_field in ERPNEXT_TO_MYMB_B2C_ITEM_MAPPING.items():
		value = item.get(erpnext_field)
		if value is not None:
			item_json[uni_field] = value

	item_json["enabled"] = not bool(item.get("disabled"))

	for barcode in item.barcodes:
		if not item_json.get("scanIdentifier"):
			# Set first barcode as scan identifier
			item_json["scanIdentifier"] = barcode.barcode
		if barcode.barcode_type == "EAN":
			item_json["ean"] = barcode.barcode
		elif barcode.barcode_type == "UPC-A":
			item_json["upc"] = barcode.barcode

	item_json["categoryCode"] = frappe.db.get_value(
		"Item Group", item.item_group, PRODUCT_CATEGORY_FIELD
	)
	# append site prefix to image url
	item_json["imageUrl"] = get_url(item.image)

	return item_json


def _handle_mymb_item(item_code: ItemCode) -> None:
	mymb_item = frappe.db.get_value(
		"Mymb Item", {"integration": MODULE_NAME, "erpnext_item_code": item_code}
	)

	if mymb_item:
		frappe.db.set_value("Mymb Item", mymb_item, "item_synced_on", now())
	else:
		frappe.get_doc(
			{
				"doctype": "Mymb Item",
				"integration": MODULE_NAME,
				"erpnext_item_code": item_code,
				"integration_item_code": item_code,
				"sku": item_code,
				"item_synced_on": now(),
			}
		).insert(ignore_permissions=True)


def validate_item(doc, method=None):
	"""Validate Item:

	1. item_code should  fulfill mymb_b2c SKU code requirements.
	2. Selected item group should have mymb_b2c product category.

	ref: http://support.mymb_b2c.com/index.php/knowledge-base/q-what-is-an-item-master-how-do-we-add-update-an-item-master/"""

	item = doc
	settings = frappe.get_cached_doc(SETTINGS_DOCTYPE)

	if not settings.is_enabled() or not item.sync_with_mymb_b2c:
		return

	if not MYMB_B2C_SKU_PATTERN.fullmatch(item.item_code):
		msg = _("Item code is not valid as per Mymb b2c requirements.") + "<br>"
		msg += _("Mymb b2c allows 3-45 character long alpha-numeric SKU code") + " "
		msg += _("with four special characters: . _ - /")
		frappe.throw(msg, title="Invalid SKU for Mymb b2c")

	item_group = frappe.get_cached_doc("Item Group", item.item_group)
	if not item_group.get(PRODUCT_CATEGORY_FIELD):
		frappe.throw(
			_("Mymb b2c Product category required in Item Group: {}").format(item_group.name)
		)


def upload_mymb_b2c_kafka(doc, method=None):
	"""This hook is called when inserting new or updating existing `Item`.

	New items are pushed to shopify and changes to existing items are
	updated depending on what is configured in "Shopify Setting" doctype.
	"""