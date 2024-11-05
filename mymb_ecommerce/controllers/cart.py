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
    """
    Fetch item availability information from the mymb_api_client using the provided kwargs
    and check if items are available by the date specified for each item in the request.
    
    Args:
        **kwargs: Parameters containing 'item_list' with items and their details, each with a specific date.

    Returns:
        Dict[str, Any]: List of available items and an array of items not available by the specified date.
    """
    try:
        client = _get_mymb_api_client_house()
        result = client.info_availability_for_item(args=kwargs)
        
        # Accessing 'GetInfoDisponibilitaATPXArticoloResult' based on the response structure
        info_availability = result.get("GetInfoDisponibilitaATPXArticoloResult", {}).get("Item", [])
        
        if not info_availability:
            return {"error": "'Item' not found in 'GetInfoDisponibilitaATPXArticoloResult'"}
        
        # Parse item_list from kwargs to get the requested dates for each internalCode
        item_list = kwargs.get("item_list", [])
        
        # Convert item_list to a dictionary for easy lookup by internalCode
        requested_items = {item["internalCode"]: item["date"] for item in item_list}
        
        from datetime import datetime
        items_not_available = []
        
        # Check each item's availability against the requested date in item_list
        for item in info_availability:
            item_code = item.get("internalCode")
            item_date_str = item.get("date", None)
            
            # Only proceed if the item_code exists in the requested_items dictionary
            if item_code in requested_items:
                # Get the requested date for this item
                requested_date_str = requested_items[item_code]
                requested_date_obj = datetime.strptime(requested_date_str, "%d/%m/%Y")
                
                # If there is no available date, add to items_not_available
                if not item_date_str:
                    items_not_available.append({
                        "internalCode": item_code,
                        "available_date": _("Not available"),
                        "requested_date": requested_date_str
                    })
                    continue
                
                # Parse the item's available date
                item_date_obj = datetime.strptime(item_date_str, "%d/%m/%Y %H:%M:%S")
                
                # If the item's available date is after the requested date, add it to items_not_available
                if item_date_obj > requested_date_obj:
                    items_not_available.append({
                        "internalCode": item_code,
                        "available_date": item_date_str,
                        "requested_date": requested_date_str
                    })
        
        # Return available items and items not available by the specified date
        return {
            "available_items": info_availability,
            "items_not_available": items_not_available
        }
    
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
        message_text = update_result.get("Message", "No additional message provided")
        
        if return_code == 0:
            # Success case
            return {
                "status": "success",
                "message": "Cart row updated successfully",
                "details": message_text
            }
        else:
            # Log error if ReturnCode is not 0
            frappe.log_error(
                message=f"Failed to update cart row with date; ReturnCode: {return_code}, Message: {message_text}",
                title="update_cart_row_with_date Error"
            )
            return {
                "status": "error",
                "error": "Failed to update cart row with date",
                "return_code": return_code,
                "message": message_text
            }
        
    except Exception as e:
        # Catch any unexpected exceptions and log them
        frappe.log_error(
            message=f"An error occurred while updating cart row with date: {str(e)}; Parameters: {kwargs}",
            title="update_cart_row_with_date Processing Error"
        )
        return {
            "status": "error",
            "error": "Processing Error",
            "message": str(e),
            "params": kwargs
        }
