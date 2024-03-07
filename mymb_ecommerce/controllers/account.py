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
from mymb_ecommerce.utils.APIClient import APIClient

JsonDict = Dict[str, Any]





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
def get_customer(customer_code):
    """Fetch customer from the mymb_api_client using the provided kwargs."""
    try:
        client = _get_mymb_api_client()
        customer = client.get_customer(customer_code)
        if customer:
            return customer.get("GetClienteResult" , "")
        else:
            return {"error": "No customer found with given code."}
    except Exception as e:
         # Handle exceptions and errors, and return a meaningful message
        frappe.log_error(f"Error while fetching orders: {e}", "Get Customer Error")
        return {
            "status": "error",
            "message": str(e)
        }
    
@frappe.whitelist(allow_guest=True)
def get_addresses(customer_code):
    """Fetch customer adresses from the mymb_api_client using the provided kwargs."""
    try:
        client = _get_mymb_api_client()
        addresses = client.get_addresses(customer_code)
        if addresses:
            return addresses.get("GetIndirizziClienteResult" , "")
        else:
            return {"error": "No address found with given code."}
    except Exception as e:
         # Handle exceptions and errors, and return a meaningful message
        frappe.log_error(f"Error while fetching orders: {e}", "Get Adresses Error")
        return {
            "status": "error",
            "message": str(e)
        }
    
@frappe.whitelist(allow_guest=True)
def payment_deadline(customer_code):
    """Fetch payment_deadline deadline from the mymb_api_client using the provided kwargs."""
    try:
        client = _get_mymb_api_client()
        payment_deadline = client.payment_deadline(customer_code)
        if payment_deadline:
            return payment_deadline.get("GetListaScadenzeConInfoResult" , "")
        else:
            return {"error": "No deadline found with given code."}
    except Exception as e:
         # Handle exceptions and errors, and return a meaningful message
        frappe.log_error(f"Error while fetching orders: {e}", "Get Deadline Error")
        return {
            "status": "error",
            "message": str(e)
        }
    
@frappe.whitelist(allow_guest=True)
def exposition(customer_code):
    """Fetch exposition from the mymb_api_client using the provided kwargs."""
    try:
        client = _get_mymb_api_client()
        exposition = client.exposition(customer_code)
        if exposition:
            return exposition.get("GetEsposizioneClienteInfoResult" , "")
        else:
            return {"error": "No deadline found with given code."}
    except Exception as e:
         # Handle exceptions and errors, and return a meaningful message
        frappe.log_error(f"Error while fetching orders: {e}", "Get Deadline Error")
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
        invoices = client.get_invoices(args=kwargs)
        if invoices:
            # Filter out invoices where CausaleDocDefinitivo is "SC"
            filtered_invoices = [invoice for invoice in invoices if invoice.get('CausaleDocDefinitivo') != "V1"]
            if filtered_invoices:
                return filtered_invoices
            else:
                return {"error": _("No invoices found with given code.")}
        else:
            return {"error": _("No invoices found with given code.")}
        
    except Exception as e:
        # Handle exceptions and errors, and return a meaningful message
        frappe.log_error(f"Error while fetching ddt: {e}", "Get Invoices Error")
        return {
            "status": "error",
            "message": str(e)
        }


@frappe.whitelist(allow_guest=True)
def pdf_tracking_order(**kwargs):
    config = Configurations()
    try:
        result = APIClient.request(
            endpoint='pdf_tracking_order',
            method='POST',
            body=kwargs,
            base_url=config.get_api_drupal()
        )

        # Check if there's a result at index 0
        if result and result[0]:
            return result[0]
        else:
            raise ValueError("No valid data found in the result.")
            
    except Exception as e:
        # Handle exceptions and errors, and return a meaningful message
        frappe.log_error(f"Error while fetching PDF tracking order: {e}", "PDF Tracking Order Error")
        return {
            "status": "error",
            "message": str(e)
        }


@frappe.whitelist(allow_guest=True)
def pdf_barcode_document(**kwargs):
    config = Configurations()
    try:
        result = APIClient.request(
            endpoint='pdf_barcode_document',
            method='POST',
            body=kwargs,
            base_url=config.get_api_drupal()
        )

        #Check if there's a result at index 0
        if result[0]:
            return result[0]
        else:
            raise ValueError("No valid data found in the result.")
            
    except Exception as e:
        # Handle exceptions and errors, and return a meaningful message
        frappe.log_error(f"Error while fetching PDF barcode document: {e}", "PDF Barcode Document Error")
        return {
            "status": "error",
            "message": str(e)
        }


@frappe.whitelist(allow_guest=True)
def invoice_pdf(**kwargs):
    config = Configurations()
    try:
        result = APIClient.request(
            endpoint='get_invoice_pdf',
            method='POST',
            body=kwargs,
            base_url=config.get_api_drupal()
        )

        # Check if there's a result at index 0
        if result[0]:
            return result[0]
        else:
            raise ValueError("No valid data found in the result.")
            
    except Exception as e:
        # Handle exceptions and errors, and return a meaningful message
        frappe.log_error(f"Error while fetching invoice PDF: {e}", "Invoice PDF Error")
        return {
            "status": "error",
            "message": str(e)
        }


@frappe.whitelist(allow_guest=True)
def csv_invoice_document(**kwargs):
    config = Configurations()
    try:
        result = APIClient.request(
            endpoint='csv_invoice_document',
            method='POST',
            body=kwargs,
            base_url=config.get_api_drupal()
        )

        # Check if there's a result at index 0
        if result and result[0]:
            return result[0]
        else:
            raise ValueError("No valid data found in the result.")
            
    except Exception as e:
        # Handle exceptions and errors, and return a meaningful message
        frappe.log_error(f"Error while fetching CSV invoice document: {e}", "CSV Invoice Document Error")
        return {
            "status": "error",
            "message": str(e)
        }

@frappe.whitelist(allow_guest=True)
def pdf_scadenzario(**kwargs):
    config = Configurations()
    try:
        result = APIClient.request(
            endpoint='pdf_scadenzario',
            method='POST',
            body=kwargs,
            base_url=config.get_api_drupal()
        )

        # Check if there's a result at index 0
        if result[0]:
            return result[0]
        else:
            raise ValueError("No valid data found in the result.")
            
    except Exception as e:
        # Handle exceptions and errors, and return a meaningful message
        frappe.log_error(f"Error while fetching invoice PDF: {e}", "Scadenziario PDF Error")
        return {
            "status": "error",
            "message": str(e)
        }
    
@frappe.whitelist(allow_guest=True)
def get_latest_order_by_item(**kwargs):
    """Fetch orders from the mymb_api_client using the provided kwargs."""
    try:
        client = _get_mymb_api_client()
        latest_orders_by_item = client.get_latest_order_by_item(args=kwargs)
        if latest_orders_by_item:
            return latest_orders_by_item
        else:
            return {"error": _("No orders found with given item.")}
        
    except Exception as e:
        # Handle exceptions and errors, and return a meaningful message
        frappe.log_error(f"Error while fetching orders: {e}", "GetUltimoOrdinatoClienteXArticolo")

        return {"error": _("No orders found with given code.")}