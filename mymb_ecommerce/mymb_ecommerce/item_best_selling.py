
# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from datetime import datetime
import frappe

import frappe
from frappe import _


# @frappe.whitelist(allow_guest=True)
def get_latest_purchased_product():
	# 	Ensure all items exist or import missing ones
    # if config.enable_mymb_b2c:
    #     missing_items = []
    #     for item in items:
    #         if not frappe.db.exists('Item', item.get("item_code")):
    #             missing_items.append(item.get("item_code"))

    #     if missing_items:
    #         # Call your import function for each missing item
    #         for missing_item_code in missing_items:
    #             filters = {"carti": missing_item_code}
    #             # Ensure to handle exceptions or check the result to confirm import success
    #             start_import_mymb_b2c_from_external_db(filters=filters, fetch_categories=True, fetch_media=True, fetch_price=True, fetch_property=True)