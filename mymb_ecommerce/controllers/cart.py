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

def _get_mymb_api_client_house():
    """Utility function to get an instance of MymbAPIClientHouse."""
    doctype_name = "Mymb Settings"
    settings = frappe.get_doc(doctype_name)
    base_url = settings.mymb_api_house
    api_username =  settings.mymb_api_username
    api_password_decypted = get_decrypted_password(doctype_name, settings.name, "mymb_api_password")
    client = MymbAPIClient(api_password=api_password_decypted, api_username=api_username,settings_doctype=doctype_name, url=base_url)
    return client

@frappe.whitelist(allow_guest=True)
def check_cart_anomalies(**kwargs):
    """Fetch orders from the mymb_api_client using the provided kwargs."""
    try:
        client = _get_mymb_api_client()
        anomalies_result = client.get_check_cart_anomalies(args=kwargs)
        result = anomalies_result.get("RisolviAnomalieDocumentoResult", {})
        # Accessing m_Item2 from the result
        m_item2 = result.get("m_Item2", None)
        if m_item2:
            return m_item2
        else:
            return {"error": "m_Item2 not found in the RisolviAnomalieDocumentoResult."}
        
    except Exception as e:
        # Handle exceptions and errors, and return a meaningful message
        frappe.log_error(f"Error while fetching anomaly: {e}", "RisolviAnomalieDocumentoResult")

        return {"error": _("No anomalies found with given code.")}
    
@frappe.whitelist(allow_guest=True)
def check_info_promotion_in_cart(**kwargs):
    """Fetch orders from the mymb_api_client using the provided kwargs."""
    try:
        client = _get_mymb_api_client()
        result = client.get_info_promotion_in_cart(args=kwargs)
        info_promotion = result.get("GetInfoPromozioneCarrelloResult", None)
        if info_promotion:
            return info_promotion
        else:
            return {"error": "info_promotion not found in the GetInfoPromozioneCarrelloResult."}
        
    except Exception as e:
        # Handle exceptions and errors, and return a meaningful message
        frappe.log_error(f"Error while fetching anomaly: {e}", "GetInfoPromozioneCarrelloResult")

        return {"error": _("No anomalies found with given code.")}
    

@frappe.whitelist(allow_guest=True)
def check_info_availability_for_item(**kwargs):
    """Fetch item availability information from the mymb_api_client using the provided kwargs."""
    try:
        client = _get_mymb_api_client_house()
        result = client.info_availability_for_item(args=kwargs)
        
        # Accessing 'GetInfoDisponibilitaATPXArticoloResult' based on the response structure
        info_availability = result.get("GetInfoDisponibilitaATPXArticoloResult", {}).get("Item", None)
        
        if info_availability:
            return info_availability
        else:
            return {"error": "'Item' not found in 'GetInfoDisponibilitaATPXArticoloResult'"}
        
    except Exception as e:
        # Handle exceptions and log errors with a meaningful message
        frappe.log_error(f"Error while fetching item availability: {e}", "GetInfoDisponibilitaATPXArticolo")
        return {"error": f"An error occurred: {str(e)}"}

@frappe.whitelist(allow_guest=True)
def update_cart_row_with_date(**kwargs):
    """
    Updates cart row with item availability information and checks for success based on the response.
    Args:
        **kwargs: Parameters for updating cart row, including item list and cart ID.
    Returns:
        Dict[str, Any]: Success message if ReturnCode is 0, otherwise an error message.
    """
    try:
        client = _get_mymb_api_client_house()
        result = client.update_cart_row_with_date(args=kwargs)
        
        # Accessing 'UpdateRigheDocumentoConDatiATPResult' based on the response structure
        update_result = result.get("UpdateRigheDocumentoConDatiATPResult", {})
        return_code = update_result.get("ReturnCode")
        
        if return_code == 0:
            # Success case
            return {"message": "Cart row updated successfully"}
        else:
            # Log error if ReturnCode is not 0
            frappe.log_error(
                message=f"Failed to update cart row with date; ReturnCode: {return_code}, Message: {update_result.get('Message')}",
                title="update_cart_row_with_date Error"
            )
            return {
                "error": "Failed to update cart row with date",
                "return_code": return_code,
                "message": update_result.get("Message", "No additional message provided")
            }
        
    except Exception as e:
        # Catch any unexpected exceptions and log them
        frappe.log_error(
            message=f"An error occurred while updating cart row with date: {str(e)}; Parameters: {kwargs}",
            title="update_cart_row_with_date Processing Error"
        )
        return {
            "error": "Processing Error",
            "message": str(e),
            "params": kwargs
        }
