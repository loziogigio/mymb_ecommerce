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
    doctype_name = "Mymb Settings"
    settings = frappe.get_doc(doctype_name)
    base_url = settings.mymb_base_api_url
    api_username =  settings.mymb_api_username
    api_password_decypted = get_decrypted_password(doctype_name, settings.name, "mymb_api_password")
    try:
        client = MymbAPIClient(api_password=api_password_decypted, api_username=api_username,settings_doctype=doctype_name, url=base_url)
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
    
@frappe.whitelist(allow_guest=True)
def get_alternative_items(
    item_code: str,
    pricing_date: Optional[str] = None,
    id_elaborazione: str = "0"
):
    """
    Frappe endpoint to get alternative item codes for a given item.
    Returns only a list of CodiceInternoArticolo values (item codes).

    Example call:
    /api/method/your_module.path.get_alternative_items?item_code=101552&id_elaborazione=0
    """
    try:
        # Initialize the API client
        client = MymbAPIClient()

        # Call the backend service to get alternative items
        response = client.get_alternative_items(
            item_code=item_code,
            pricing_date=pricing_date,
            id_elaborazione=id_elaborazione
        )

        # Extract the 'ListaPrezzatura' from the response payload
        items = response.get("ListaPrezzatura", [])

        # Collect all CodiceInternoArticolo values
        item_codes = [
            row.get("CodiceInternoArticolo")
            for row in items
            if row.get("CodiceInternoArticolo")
        ]

        # Return the list or a default error if empty
        return { "item_codes":item_codes}  or {"error": "No alternative item codes found."}

    except Exception as e:
        # Log error and return user-facing error message
        frappe.log_error(
            title="get_alternative_items error",
            message=f"Error fetching alternative items for code {item_code}: {str(e)}"
        )
        return {"error": str(e)}

