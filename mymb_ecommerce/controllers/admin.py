import base64
from typing import Any, Dict, List, Optional, Tuple

import frappe
import requests
from frappe import _
from frappe.utils import cint, cstr, get_datetime, now_datetime
from frappe.utils.password import get_decrypted_password
from pytz import timezone

from mymb_ecommerce.mymb_b2c.constants import SETTINGS_DOCTYPE
from mymb_ecommerce.settings.configurations import Configurations
from mymb_ecommerce.utils.MymbAPIClient import MymbAPIClient


JsonDict = Dict[str, Any]

config = Configurations()
mymb_api_client = MymbAPIClient()


def _get_mymb_api_client():
    """Utility function to get an instance of MymbAPIClient."""
    doctype_name = "Mymb Settings"
    settings = frappe.get_doc(doctype_name)
    base_url = settings.mymb_base_api_url
    api_username =  settings.mymb_api_username
    api_password_decypted = get_decrypted_password(doctype_name, settings.name, "mymb_api_password")
    client = MymbAPIClient(api_password=api_password_decypted, api_username=api_username,settings_doctype=doctype_name, url=base_url)
    return client


@frappe.whitelist(allow_guest=True)
def get_orders(**kwargs):
    """Fetch orders from the mymb_api_client using the provided kwargs."""
    try:
        client = _get_mymb_api_client()
        orders = client.get_orders(args=kwargs)
        if orders:
            return orders
        else:
            return {"error": _("No orders found with given code.")}
        
        # Return the result
        return response
    except Exception as e:
        # Handle exceptions and errors, and return a meaningful message
        frappe.log_error(f"Error while fetching orders: {e}", "Get Orders Error")
        return {
            "status": "error",
            "message": str(e)
        }
    
@frappe.whitelist(allow_guest=True)
def get_customer_by_code(customer_code):
    try:
        client = _get_mymb_api_client()
        customer = client.get_customer(customer_code)
        if customer:
            return customer
        else:
            return {"error": "No customer found with given code."}
    except Exception as e:
         # Handle exceptions and errors, and return a meaningful message
        frappe.log_error(f"Error while fetching orders: {e}", "Get Orders Error")
        return {
            "status": "error",
            "message": str(e)
        }
    
@frappe.whitelist(allow_guest=True)
def get_ddt(**kwargs):
    """Fetch ddt from the mymb_api_client using the provided kwargs."""
    try:
        client = _get_mymb_api_client()
        ddt = client.get_ddt(args=kwargs)
        if ddt:
            return ddt
        else:
            return {"error": _("No ddt found with given code.")}
        
        # Return the result
        return response
    except Exception as e:
        # Handle exceptions and errors, and return a meaningful message
        frappe.log_error(f"Error while fetching ddt: {e}", "Get DDT Error")
        return {
            "status": "error",
            "message": str(e)
        }
    
@frappe.whitelist(allow_guest=True)
def get_invoices(**kwargs):
    """Fetch ddt from the mymb_api_client using the provided kwargs."""
    try:
        client = _get_mymb_api_client()
        ddt = client.get_invoices(args=kwargs)
        if ddt:
            return ddt
        else:
            return {"error": _("No invoices found with given code.")}
        
        # Return the result
        return response
    except Exception as e:
        # Handle exceptions and errors, and return a meaningful message
        frappe.log_error(f"Error while fetching ddt: {e}", "Get Invoices Error")
        return {
            "status": "error",
            "message": str(e)
        }
    