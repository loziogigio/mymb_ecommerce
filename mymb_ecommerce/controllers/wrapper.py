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
from mymb_ecommerce.utils.APIClient import APIClient
from mymb_ecommerce.utils.email_lib import sendmail
from mymb_ecommerce.utils.wrapper import paginate, build_product_list, build_filter_list, wrap_product_detail, wrap_child_product_detail

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


# Get Product List
@frappe.whitelist(allow_guest=True)
def product_list(**kwargs):
    
    per_page = kwargs.get('per_page')
    page = kwargs.get('page')
    text = kwargs.get('text')
    query_args = {key: value for key, value in kwargs.items() if key not in ('per_page', 'page', 'ext_call', 'address_code', 'client_id', 'cmd')}
    body_args = {key: value for key, value in kwargs.items() if key in ('client_id', 'address_code', 'ext_call', 'per_page', 'page' )}
    query_string = '?'

    if query_args:
        query_string += '&'.join([f'{key}={value}' for key, value in query_args.items()]) + '&'

    result = APIClient.request(
        endpoint=f'catalogo{query_string}',
        method='POST',
        body=body_args,
        base_url=config.get_api_drupal()
    )

    if isinstance(result, tuple):
        result = result[0]
    else:
        result = result

    if 'response' in result and result['response'] == 'no result':
        return {
            'success': False
        }   

    build_result = paginate(build_product_list(result), per_page, result['totalCount'], result['page'], result['pages'])
    filter_list = build_filter_list(result)
    build_tab_list = result['tabs']

    return {
        'success': True,
        'product_list': build_result,
        'filters': filter_list,
        'tab_list': build_tab_list
    }

# Get Child List
@frappe.whitelist(allow_guest=True)
def child_list(**kwargs):
    
    query_string = "?"  # Initialize the query string if needed
    
    if kwargs:
        query_string += "&".join([f"{key}={value}" for key, value in kwargs.items()]) + '&'

    result = APIClient.request(
        endpoint=f'load_childs_prices{query_string}',
        method='POST',
        body=kwargs,
        base_url=config.get_api_drupal()
    )

    if isinstance(result, tuple):
        result = result[0]
    else:
        result = result

    return result

# Get Item
@frappe.whitelist(allow_guest=True)
def get_item(**kwargs):
    
    query_args = {key: value for key, value in kwargs.items() if key not in ('cmd')}
    query_string = '?'

    if query_args:
        query_string += '&'.join([f'{key}={value}' for key, value in query_args.items()]) + '&'


    result = APIClient.request(
        endpoint=f'get-item{query_string}',
        method='POST',
        body=kwargs,
        base_url=config.get_api_drupal()
    )

    if isinstance(result, tuple):
        result = result[0]
    else:
        result = result

    res = wrap_product_detail(result)

    return {
        'data': res,
        'relatedProducts': [res],
        'featuredProducts': [res],
        'bestSellingProducts': [res],
        'latestProducts': [res],
        'topRatedProducts': [res],
        'prevProduct': None,
        'nextProduct': None,
        'extra_info': result
    }

# Get Child Item
@frappe.whitelist(allow_guest=True)
def get_item_child(**kwargs):
    
    query_args = {key: value for key, value in kwargs.items() if key not in ('cmd')}
    query_string = '?'

    if query_args:
        query_string += '&'.join([f'{key}={value}' for key, value in query_args.items()]) + '&'


    result = APIClient.request(
        endpoint=f'get-item-child{query_string}',
        method='POST',
        body=kwargs,
        base_url=config.get_api_drupal()
    )

    if isinstance(result, tuple):
        result = result[0]
    else:
        result = result

    res = wrap_child_product_detail(result)

    return {
        'data': res,
        'relatedProducts': [res],
        'featuredProducts': [res],
        'bestSellingProducts': [res],
        'latestProducts': [res],
        'topRatedProducts': [res],
        'prevProduct': None,
        'nextProduct': None,
        'extra_info': result
    }

# Add To Cart
@frappe.whitelist(allow_guest=True)
def add_to_cart(**kwargs):
    
    query_args = {key: value for key, value in kwargs.items() if key not in ('cmd')}
    query_string = ''

    if query_args:
        query_string += '&'.join([f'{key}={value}' for key, value in query_args.items()]) + '&'


    result = APIClient.request(
        endpoint=f'add_to_cart?ext_call=true{query_string}',
        method='POST',
        body=kwargs,
        base_url=config.get_api_drupal()
    )

    if isinstance(result, tuple):
        result = result[0]
    else:
        result = result

    return result

# Add To Cart Promo
@frappe.whitelist(allow_guest=True)
def add_to_cart_promo(**kwargs):
    
    query_args = {key: value for key, value in kwargs.items() if key not in ('cmd')}
    query_string = ''

    if query_args:
        query_string += '&'.join([f'{key}={value}' for key, value in query_args.items()]) + '&'


    result = APIClient.request(
        endpoint=f'add_to_cart_promo?ext_call=true{query_string}',
        method='POST',
        body=kwargs,
        base_url=config.get_api_drupal()
    )

    if isinstance(result, tuple):
        result = result[0]
    else:
        result = result

    return result

# Get Cart Items
@frappe.whitelist(allow_guest=True)
def get_cart_items(**kwargs):
    
    query_args = {key: value for key, value in kwargs.items() if key not in ('cmd')}
    query_string = '?'

    if query_args:
        query_string += '&'.join([f'{key}={value}' for key, value in query_args.items()]) + '&'


    result = APIClient.request(
        endpoint=f'carrello{query_string}',
        method='POST',
        body=kwargs,
        base_url=config.get_api_drupal()
    )

    if isinstance(result, tuple):
        result = result[0]
    else:
        result = result

    return result

# Update Cart
@frappe.whitelist(allow_guest=True)
def update_cart(**kwargs):
    
    query_args = {key: value for key, value in kwargs.items() if key not in ('cmd')}
    query_string = '?'

    if query_args:
        query_string += '&'.join([f'{key}={value}' for key, value in query_args.items()]) + '&'


    result = APIClient.request(
        endpoint=f'update_cart{query_string}',
        method='POST',
        body=kwargs,
        base_url=config.get_api_drupal()
    )

    if isinstance(result, tuple):
        result = result[0]
    else:
        result = result

    return result

# Remove Cart Item
@frappe.whitelist(allow_guest=True)
def remove_cart_item(**kwargs):
    
    query_args = {key: value for key, value in kwargs.items() if key not in ('cmd')}
    query_string = '?'

    if query_args:
        query_string += '&'.join([f'{key}={value}' for key, value in query_args.items()]) + '&'


    result = APIClient.request(
        endpoint=f'delete_riga{query_string}',
        method='POST',
        body=kwargs,
        base_url=config.get_api_drupal()
    )

    if isinstance(result, tuple):
        result = result[0]
    else:
        result = result

    return result

# Remove Cart
@frappe.whitelist(allow_guest=True)
def remove_cart(**kwargs):
    
    id_cart=kwargs.get('id_cart','')
    query_string = f'{id_cart}?ext_call=true'

    result = APIClient.request(
        endpoint=f'delete_cart/{query_string}',
        method='POST',
        base_url=config.get_api_drupal()
    )

    if isinstance(result, tuple):
        result = result[0]
    else:
        result = result

    return result

# Prepare Order
@frappe.whitelist(allow_guest=True)
def prepare_order(**kwargs):
    
    query_args = {key: value for key, value in kwargs.items() if key not in ('cmd')}
    query_string = '?'

    if query_args:
        query_string += '&'.join([f'{key}={value}' for key, value in query_args.items()]) + '&'


    result = APIClient.request(
        endpoint=f'cassa{query_string}',
        method='POST',
        body=kwargs,
        base_url=config.get_api_drupal()
    )

    return result

# Send Order
@frappe.whitelist(allow_guest=True)
def send_order(**kwargs):
    
    result = APIClient.request(
        endpoint=f'send_order',
        method='POST',
        body=kwargs,
        base_url=config.get_api_drupal()
    )

    return result

# Get Order Detail
@frappe.whitelist(allow_guest=True)
def get_order_detail(**kwargs):
    numero_doc_definitivo = kwargs.get('NumeroDocDefinitivo')
    causale_doc_definitivo = kwargs.get('CausaleDocDefinitivo')
    anno_doc_definitivo = kwargs.get('AnnoDocDefinitivo')

    endpoint = f'tracking_ordine/{numero_doc_definitivo}/{causale_doc_definitivo}/{anno_doc_definitivo}'
    
    query_args = {key: value for key, value in kwargs.items() if key not in ('NumeroDocDefinitivo', 'CausaleDocDefinitivo', 'AnnoDocDefinitivo', 'cmd')}
    query_string = '?'

    if query_args:
        query_string += '&'.join([f'{key}={value}' for key, value in query_args.items()]) + '&'


    result = APIClient.request(
        endpoint=f'{endpoint}{query_string}',
        method='get',
        body=kwargs,
        base_url=config.get_api_drupal()
    )

    if isinstance(result, tuple):
        result = result[0]
    else:
        result = result

    return result

# Get Autocomplete Items
@frappe.whitelist(allow_guest=True)
def autocomplete(**kwargs):

    query_args = {key: value for key, value in kwargs.items() if key not in ('cmd')}
    query_string = '?'

    if query_args:
        query_string += '&'.join([f'{key}={value}' for key, value in query_args.items()]) + '&'

    result = APIClient.request(
        endpoint=f'autocomplete.php{query_string}',
        method='get',
        base_url=config.get_api_drupal()
    )

    if result is None:
        return {
            'success': False,
            'message': _('API request failed!')
        }, 500


    if isinstance(result, tuple):
        result = result[0]
    else:
        result = result

   
    return {
        'result': result.get('response', {}).get('docs', [])
    }

# Get Account Info
@frappe.whitelist(allow_guest=True)
def account(**kwargs):

    query_args = {key: value for key, value in kwargs.items() if key not in ('cmd')}
    query_string = f'?'

    if query_args:
        query_string += '&'.join([f'{key}={value}' for key, value in query_args.items()]) + '&'

    result = APIClient.request(
        endpoint=f'pipe.php{query_string}',
        method='get',
        base_url=config.get_api_drupal()
    )

    if isinstance(result, tuple):
        result = result[0]
    else:
        result = result

    if result is None:
        return {
            'success': False,
            'message': _('API request failed!')
        }, 500

    return result