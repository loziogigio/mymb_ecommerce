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
from mymb_ecommerce.repository.TmpCarrelloDettagliRepository import TmpCarrelloDettagliRepository
from datetime import datetime


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
                    # Update delivery_date in cart_rows if it's missing
                



@frappe.whitelist(allow_guest=True)
def check_info_availability_for_item(**kwargs):
    """
    Fetch item availability information, check if items are available by the specified date,
    and add 'delivery_date' to the response based on existing data or item date, or "N/A" if not available.
    """
    try:
        client = _get_mymb_api_client_house()
        result = client.info_availability_for_item(args=kwargs)
        id_cart = kwargs.get("id_cart")
        if not id_cart:
            frappe.throw("Cart ID (id_cart) is required", frappe.MandatoryError)

        # Accessing 'GetInfoDisponibilitaATPXArticoloResult'
        info_availability = result.get("GetInfoDisponibilitaATPXArticoloResult", {}).get("Item", [])
        if not info_availability:
            return {"error": "'Item' not found in 'GetInfoDisponibilitaATPXArticoloResult'"}

        # Get the requested dates from item_list
        item_list = kwargs.get("item_list", [])
        requested_items = {item["internalCode"]: item["date"] for item in item_list}
        
        # Initialize repository to retrieve cart rows and set delivery dates
        repository = TmpCarrelloDettagliRepository()
        cart_rows = repository.get_all_records(id_carrello=id_cart, to_dict=True)
        # Check if all delivery_date fields are empty
        first_update = not any(row['delivery_date'] for row in cart_rows)

        items_not_available = []

        # Check each item in info_availability and set 'delivery_date' in the response
        for item in info_availability:
            item_code = item.get("internalCode")
            item_date_str = item.get("date", None)
            delivery_date_str = "N/A"  # Default to "N/A" if no delivery date is found
            
            # Set and update delivery_date, if we have the value in db we return it otherwise we edit in db and we return the same value
            if item_code in requested_items:
                for row in cart_rows:
                    if row['oarti'] == item_code and item_date_str:
                        if  not row['delivery_date']:
                            delivery_date_obj = datetime.strptime(item_date_str, "%d/%m/%Y %H:%M:%S")
                            delivery_date_str = delivery_date_obj.strftime("%d/%m/%Y")
                            
                            #first we update the client 
                            client = _get_mymb_api_client_house()
                              # Format delivery_option for the single item request
                            delivery_option = {
                                "item_list": [
                                    {
                                        "internalCode": item_code,
                                        "quantity": row.get("quantity", 1),  # Use a default quantity if not available
                                        "date": delivery_date_str
                                    }
                                ],
                                "id_cart": id_cart
                            }
                            result = client.update_cart_row_with_date(args=delivery_option)
                            # Check and log if ReturnCode is not 0
                            return_code = result.get("ReturnCode")
                            if return_code != 0:
                                message_text = result.get("Message", f"No additional message provided {delivery_option}" )
                                frappe.log_error(
                                    message=f"Failed to update cart row with date; ReturnCode: {return_code}, Message: {message_text} {delivery_option}",
                                    title="update_cart_row_with_date Error"
                                )
        
                            repository.update_delivery_date(id_carrello=id_cart, internal_code=item_code, delivery_date=delivery_date_str)

                        else:
                            delivery_date_str=row['delivery_date'].strftime("%d/%m/%Y")
                
                # Add delivery_date to info_availability item
                item["delivery_date"] = delivery_date_str

                # If no available date, mark as not available
                requested_date_str = requested_items[item_code]
                requested_date_obj = datetime.strptime(requested_date_str, "%d/%m/%Y")
                
                #We skip item with not date
                if not item_date_str:
                    continue
                    

                # Parse available date and check against requested date
                item_date_obj = datetime.strptime(item_date_str, "%d/%m/%Y %H:%M:%S")
                if item_date_obj > requested_date_obj:
                    items_not_available.append({
                        "internalCode": item_code,
                        "available_date": item_date_str,
                        "requested_date": requested_date_str,
                        "delivery_date": delivery_date_str
                    })

            
        return {
            "available_items": info_availability,
            "items_not_available": items_not_available,
            "first_update":first_update
        }

    except Exception as e:
        frappe.log_error(f"Error while fetching item availability: {e}", "GetInfoDisponibilitaATPXArticolo")
        return {"error": f"An error occurred: {str(e)}"}




@frappe.whitelist(allow_guest=True)
def update_cart_row_with_date(**kwargs):
    """
    Updates cart row with item availability information and checks for success based on the response.
    If 'delivery_date' is not set in the cart row, it is updated with the provided date.
    
    Args:
        **kwargs: Parameters for updating cart row, including item list and cart ID.

    Returns:
        Dict[str, Any]: Success message if ReturnCode is 0, otherwise an error message.
    """
    
    try:
        id_cart = kwargs.get("id_cart")
        if not id_cart:
            frappe.throw("Cart ID (id_cart) is required", frappe.MandatoryError)

        client = _get_mymb_api_client_house()
        result = client.update_cart_row_with_date(args=kwargs)

        # Accessing 'UpdateRigheDocumentoConDatiATPResult' based on the response structure
        update_result = result.get("UpdateRigheDocumentoConDatiATPResult", {})
        return_code = update_result.get("ReturnCode")
        message_text = update_result.get("Message", "No additional message provided")
        
        # Check if the update on the external API was successful
        if return_code == 0:
            item_list = kwargs.get("item_list", [])

            # Initialize repository to retrieve and update cart rows
            repository = TmpCarrelloDettagliRepository()

            # Update delivery_date in cart rows if not already set
            for item in item_list:
                internal_code = item.get("internalCode")
                date_str = item.get("date")
                if date_str:
                    repository.update_delivery_date(id_carrello=id_cart, internal_code=internal_code, delivery_date=date_str)
            # Prepare arguments to retrieve updated cart rows
            id_cart_dic = {"id_cart": id_cart}
            item_list_with_delivery_date = get_cart_rows_by_id_cart(**id_cart_dic)
            return {
                "status": "success",
                "message": "Cart row updated successfully",
                "item_list_with_delivery_date" : item_list_with_delivery_date,
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


@frappe.whitelist(allow_guest=True)
def get_cart_rows_by_id_cart(**kwargs):
    # Extract the `id_carrello` from kwargs
    id_cart = kwargs.get("id_cart")

    if not id_cart:
        frappe.throw("Cart ID (id_cart) is required", frappe.MandatoryError)
    
    # Initialize the repository
    repository = TmpCarrelloDettagliRepository()

    # Fetch records filtered by id_carrello
    try:
        cart_records = repository.get_all_records(id_carrello=id_cart , to_dict=True)

        # Convert date and delivery_date to dd/mm/yyyy format
        for record in cart_records:
            if 'delivery_date' in record and isinstance(record['delivery_date'], datetime):
                record['delivery_date'] = record['delivery_date'].strftime("%d/%m/%Y")


    except Exception as e:
        frappe.log_error(f"Error fetching cart records: {str(e)}")
        frappe.throw("An error occurred while fetching cart details.")

    return cart_records


@frappe.whitelist(allow_guest=True)
def update_delivery_date(**kwargs):
    # Extract the data from kwargs
    item_list = kwargs.get("item_list")
    id_cart = kwargs.get("id_cart")

    if not id_cart or not item_list:
        frappe.throw("Both Cart ID (id_cart) and item_list are required.", frappe.MandatoryError)

    # Initialize the repository
    repository = TmpCarrelloDettagliRepository()

    # Process each item in the item_list
    results = []
    for item in item_list:
        internal_code = item.get("internalCode")
        date_str = item.get("date")

        # Call repository method to update delivery_date
        result = repository.update_delivery_date(id_cart, internal_code, date_str)
        results.append(result)

    return results