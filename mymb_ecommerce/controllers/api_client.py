import base64
from typing import Any, Dict, List, Optional, Tuple

import frappe
import requests
from frappe import _
from frappe.utils import cint, cstr, get_datetime
from pytz import timezone

from mymb_ecommerce.mymb_b2c.constants import SETTINGS_DOCTYPE
from mymb_ecommerce.utils.MymbAPIClient import MymbAPIClient
from frappe.utils.password import get_decrypted_password

JsonDict = Dict[str, Any]


@frappe.whitelist(allow_guest=True)
def get_customer_by_code(customer_code):
    try:
        client = MymbAPIClient()
        customer = client.get_customer(customer_code)
        if customer:
            return customer
        else:
            return {"error": "No customer found with given code."}
    except Exception as e:
        return {"error": str(e)}
    
@frappe.whitelist(allow_guest=True)
def get_products_price(
    customer_code: str,
    address_code: str,
    item_codes: str,  # pass items as comma-separated string
    quantity_list: str,  # pass quantities as comma-separated string
    id_cart: str
):
    try:
        client = MymbAPIClient()
        item_codes = item_codes.split(',')
        quantity_list = [int(qty) for qty in quantity_list.split(',')]
        prices = client.get_multiple_prices(customer_code, address_code, item_codes, quantity_list, id_cart)
        if prices:
            return prices
        else:
            return {"error": "No prices found with given parameters."}
    except Exception as e:
        return {"error": str(e)}