import base64
from typing import Any, Dict, List, Optional, Tuple

import frappe
import requests
from frappe import _
from frappe.utils import cint, cstr, get_datetime, now_datetime
from pytz import timezone

from mymb_ecommerce.mymb_b2c.constants import SETTINGS_DOCTYPE
from mymb_ecommerce.settings.configurations import Configurations
from mymb_ecommerce.utils.APIClient import APIClient
from frappe.utils.password import get_decrypted_password
from mymb_ecommerce.utils.email_lib import sendmail

JsonDict = Dict[str, Any]

config = Configurations()


@frappe.whitelist(allow_guest=True)
def login(**kwargs):
    # Making a POST request using the provided keyword arguments (kwargs).
    response = APIClient.request(
        endpoint='login.php',
        method='POST',
        body=kwargs,
        base_url=config.get_api_drupal()
    )

    if response is None:
        return {
            'success': False,
            'message': _('API request failed!')
        }, 500

    result, success = response

    if success:
        return result  # directly return the API response
    else:
        return {
            'success': False,
            'message': _('Authentication Failed!')
        }, 422

# Register   
@frappe.whitelist(allow_guest=True)
def register(**kwargs):
    try:
        # Extract data from the kwargs dictionary
        name = kwargs.get('name')
        email = kwargs.get('email')
        vat = kwargs.get('vat')
        phone = kwargs.get('phone')

        # Compose your email message
        subject = "Welcome Message"
        message = f"Hello {name},\n\nWelcome to our platform!\n\n"
        message += f"Email: {email}\n"
        message += f"VAT: {vat}\n"
        message += f"Phone: {phone}\n\n"
        message += "Thank you for registering with us."

        # Send the email
        sendmail(
            recipients=email,
            sender=email,
            subject=subject,
            message=message,
        )

        return {
            'success': True
        }
    except Exception as e:
        return {
            'success': False,
            'message': str(e)
        }
