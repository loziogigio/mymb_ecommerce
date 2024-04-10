import base64
from typing import Any, Dict, List, Optional, Tuple

import frappe
import requests
from frappe import _
from frappe.utils import cint, cstr, get_datetime, now_datetime
from frappe.utils.password import get_decrypted_password
from pytz import timezone

from mymb_ecommerce.mymb_b2c.constants import SETTINGS_DOCTYPE
from mymb_ecommerce.utils.MymbAPIClient import MymbAPIClient
from mymb_ecommerce.utils.APIClient import APIClient

from mymb_ecommerce.mymb_b2c.settings.configurations import Configurations

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

import frappe
from frappe import _

@frappe.whitelist(allow_guest=True, methods=['POST'])  # Changed to 'GET' as you're fetching data
def get_invoice_service(causale, anno, numero, tipo_documento=""):
    # Assuming the Configurations class has a method to get the base URL
    config = Configurations()
    base_url = config.url_doc_public_service  # Ensure this returns something like "http://example.com/"

    # Construct the full URL with query parameters
    full_url = f"{base_url}web/GetFileArchiviatoFromPkDoc?Causale={causale}&Anno={anno}&Numero={numero}&TipoDocumento={tipo_documento}"

    # Make the GET request
    try:
        response = frappe.client.get(full_url)
        if response.status_code == 200:
            # Assuming the response is JSON and you want to return it directly
            return response.json()
        else:
            frappe.throw(_("Failed to fetch the document. Status code: {0}").format(response.status_code))
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "get_invoice_service Failed")
        frappe.throw(_("Failed to fetch the document due to an error: {0}").format(e))
