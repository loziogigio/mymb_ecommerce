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
    


    