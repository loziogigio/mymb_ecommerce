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
from mymb_ecommerce.utils.wrapper import paginate, build_product_list, build_filter_list, build_filter_group_list,  wrap_product_detail, wrap_child_product_detail , build_category_breadcrumbs

from frappe.utils.pdf import get_pdf
import os

JsonDict = Dict[str, Any]




@frappe.whitelist(allow_guest=True)
def login(**kwargs):
    # Making a POST request using the provided keyword arguments (kwargs).
    config = Configurations()
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


@frappe.whitelist(allow_guest=True)
def product_list(**kwargs):
    try:
        config = Configurations()
        per_page = kwargs.get('per_page')

        # Remove 'cmd' if present
        kwargs.pop('cmd', None)

        # Remove 'text' if any of these keys are present
        # if any(key in kwargs for key in ['purchased', 'disponibili', 'promo_list', 'new', 'next_insert']):
        #     kwargs.pop('text', None)

        # Define which keys go in the body of the request
        body_keys = ['client_id', 'address_code', 'ext_call', 'per_page', 'page']
        body_args = {key: value for key, value in kwargs.items() if key in body_keys}
        query_args = {key: value for key, value in kwargs.items() if key not in body_keys}

        # Build query string
        query_string = '?' + '&'.join([f'{key}={value}' for key, value in query_args.items()]) if query_args else ''

        # Make the API request
        result = APIClient.request(
            endpoint=f'catalogo{query_string}',
            method='POST',
            body=body_args,
            base_url=config.get_api_drupal()
        )

        if isinstance(result, tuple):
            result = result[0]

        csoci = result.get('csoci',None)

        if 'response' in result and result['response'] == 'no result':
            return {'success': False}

        build_result = paginate(build_product_list(result), per_page, result['totalCount'], result['page'], result['pages'])
        filter_list = build_filter_list(result)
        if csoci:
            filter_list = build_filter_group_list(filter_list , csoci)
            
        build_tab_list = result['tabs']
        #Add category breadcrumbs only if present
        category_query = kwargs.get('category')
        if category_query and csoci:
            breadcrumbs = build_category_breadcrumbs(category_query, csoci)
            if breadcrumbs:
                build_tab_list["category"] = breadcrumbs

        return {
            'success': True,
            'product_list': build_result,
            'filters': filter_list,
            'tab_list': build_tab_list,
            'api': config.get_api_drupal()
        }

    except Exception as e:
        # Log full details: error, input kwargs, and result if available
        frappe.log_error(
            title="product_list error",
            message=f"Exception: {str(e)}\n\nRequest kwargs:\n{kwargs}"
        )
        return {'success': False, 'error': 'Internal Server Error'}


# Get Child List
@frappe.whitelist(allow_guest=True)
def child_list(**kwargs):
    config = Configurations()
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
    config = Configurations()
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
    config = Configurations()
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
    config = Configurations()
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
    config = Configurations()
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
    config = Configurations()
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
    config = Configurations()
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
    config = Configurations()
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
    config = Configurations()
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
    config = Configurations()
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

@frappe.whitelist(allow_guest=True)
def get_order_pdf(**kwargs):
    data = get_cart_items(**kwargs)
        # Check if the custom email template exists
    email_template_name = 'custom-order-template'
    if frappe.db.exists("Email Template", email_template_name):
        email_template = frappe.get_doc("Email Template", email_template_name)
    # Else if the general email template exists by removing 'custom-'
    elif frappe.db.exists("Email Template", email_template_name.replace('custom-', '', 1)):
        email_template = frappe.get_doc("Email Template", email_template_name.replace('custom-', '', 1))
    # Use any available template as the last resort
    else:
        default_email_templates = frappe.get_all("Email Template", limit=1)
        if not default_email_templates:
            return {"status": "Failed", "message": "No email template found."}
        email_template = frappe.get_doc("Email Template", default_email_templates[0].name)

    # If the first element of the tuple is the actual dictionary, do this:
    if isinstance(data, tuple):
        data = data[0]  # Extract the first element which should be the dictionary
    # Prepare the email context
    context = {
        'data':data
    }
    rendered_email_content = frappe.render_template(email_template.response_, context)

    # Generate the PDF from the rendered content
    pdf_content = get_pdf(rendered_email_content)

    # Encode the PDF content in base64
    pdf_base64 = base64.b64encode(pdf_content).decode('utf-8')

    # Return the base64 PDF as part of the JSON response
    return {
        "status": "Success",
        "pdf_base64": pdf_base64,
        "filename": f"order_{kwargs.get('id_cart') or 'unknown'}.pdf"
    }



# Send Order
@frappe.whitelist(allow_guest=True)
def send_order(**kwargs):
    config = Configurations()
    result = APIClient.request(
        endpoint=f'send_order',
        method='POST',
        body=kwargs,
        base_url=config.get_api_drupal()
    )

    return result

@frappe.whitelist(allow_guest=True)
def set_payment_completed(cart_id: int = None, success: bool = None, trandaction_id: str = None):
    if not cart_id or not trandaction_id:
        frappe.throw("Missing required parameters: cart_id or trandaction_id.")

    config = Configurations()

    payload = {
        "cart_id": cart_id,
        "success": success,
        "trandaction_id": trandaction_id
    }

    # Call the external service
    result = APIClient.request(
        endpoint='ipn-paypal',
        method='POST',
        body=payload,
        base_url=config.get_api_drupal()
    )

    # Unpack response if it's a tuple (dict, status)
    response_dict, _ = result if isinstance(result, tuple) else (result, False)

    # Extract response safely
    result_data = response_dict.get("result", {}) if isinstance(response_dict, dict) else {}
    status = result_data.get("status", False)
    response_service = result_data.get("response_service", {})

    # If failed, log it
    if not status:
        frappe.log_error(
            title=f"fail - complete order {cart_id}",
            message=(
                f"cart_id: {cart_id}\n"
                f"transaction_id: {trandaction_id}\n"
                f"response: {frappe.as_json(response_service)}"
            )
        )

    return {
        "result": {
            "response_service": response_service,
            "status": status
        },
        "id_carrello": cart_id,
        "transaction_id": trandaction_id
    }


# Get Order Detail
@frappe.whitelist(allow_guest=True)
def get_order_detail(**kwargs):
    config = Configurations()
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
    config = Configurations()
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
    config = Configurations()
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

# Save Cart
@frappe.whitelist(allow_guest=True)
def save_cart(**kwargs):
    config = Configurations()
    result = APIClient.request(
        endpoint=f'save_prev',
        method='POST',
        body=kwargs,
        base_url=config.get_api_drupal()
    )

    return result

# Save Cart
@frappe.whitelist(allow_guest=True)
def activate_cart(**kwargs):
    config = Configurations()
    ##Placeing static 0/0 data because the real one are sen via post
    result = APIClient.request(
        endpoint=f'attiva_carrello/0/0',
        method='POST',
        body=kwargs,
        base_url=config.get_api_drupal()
    )

    return result


@frappe.whitelist(allow_guest=True)
def reset_password(**kwargs):
    # Making a POST request using the provided keyword arguments (kwargs).
    config = Configurations()
    response = APIClient.request(
        endpoint='reset_password.php',
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
        recipient_email = result.get('username')        
        if kwargs.get('password') != None:
            context = f'Email:{recipient_email}'
            send_general_email(recipient_email  , context, email_template="update-password-email")
        else:
            new_password = result.get('new_password')
            context = f'Email:{recipient_email} Password:{new_password} '
            send_general_email(recipient_email  , context, email_template="reset-password-email")
        return  {
            'success': True,
            'message': _('Request succes')
        }, 200
    else:
        return {
            'success': False,
            'message': _('Authentication Failed!')
        }, 422



def send_general_email(recipient_email, context_string, email_template="custom-standard-email"):
    config = Configurations()
    
    # Fetch sender email from Configurations or fallback to Email Account settings
    sender_email = config.get_no_reply_email()
    
    if not sender_email:
        sender_email = frappe.db.get_single_value("Email Account", "email_id")

    # Check if the custom email template exists
    if frappe.db.exists("Email Template", email_template):
        email_template = frappe.get_doc("Email Template", email_template)
    # else if the general email template exists by remove 'custom-'
    elif frappe.db.exists("Email Template",  email_template.replace('custom-', '', 1)):
        email_template = frappe.get_doc("Email Template",  email_template.replace('custom-', '', 1))
    else:
        default_email_templates = frappe.get_all("Email Template", limit=1)
        if not default_email_templates:
            return {"status": "Failed", "message": "No email template found."}
        email_template = frappe.get_doc("Email Template", default_email_templates[0].name)
        

    recipients = [recipient_email]   # Assuming 'recipient_email' is the field in Sales Order for customer's email

    
    context = {
        "context":context_string
        # ... you can add other context variables as needed
    }
    try:
        # Render the email content with the context
        rendered_email_content = frappe.render_template(email_template.response_, context)
        rendered_subject = frappe.render_template(email_template.subject, context)

        # Send email
        # Prepare email arguments
        email_args = {
            "recipients": recipients,
            "subject": rendered_subject,
            "message": rendered_email_content,
        }

        if sender_email:
            email_args["sender"] = sender_email

        # Send email
        frappe.sendmail(**email_args)

        return {"status": "Success", "message": "Email sent successfully."}
    except Exception as e:
        # Log the error
        frappe.log_error(message=f"Error sending sales order confirmation email for context: {context}: {str(e)}", title=f"Email Error {recipient_email}")

        # Return a response indicating that there was an error
        return {"status": "Failed", "message": f"Error encountered: {str(e)}"}
    

@frappe.whitelist(allow_guest=True)
def send_generic_email(data={}, email_template_name="generic_email", recipients=None):

    config = Configurations()
    
    # Fetch sender email from Configurations or fallback to Email Account settings
    sender_email = config.get_no_reply_email()
    
    if not sender_email:
        sender_email = frappe.db.get_single_value("Email Account", "email_id")

    # Check if recipients are provided; if not, do not send the email.
    if not recipients:
        return {"status": "Failed", "message": "No recipients provided. Email not sent."}

    # Attempt to fetch the specified email template.
    if frappe.db.exists("Email Template", email_template_name):
        email_template = frappe.get_doc("Email Template", email_template_name)
    else:
        # If the specified template doesn't exist, fetch a default one.
        default_email_templates = frappe.get_all("Email Template", limit=1)
        if not default_email_templates:
            return {"status": "Failed", "message": "No email template found."}
        email_template = frappe.get_doc("Email Template", default_email_templates[0].name)

    # Prepare the context for rendering the template.
    context = {
        "data": data,
        # ... add other context variables as needed.
    }

    try:
        # Render the email content and subject using the context.
        rendered_email_content = frappe.render_template(email_template.response_, context)
        rendered_subject = frappe.render_template(email_template.subject, context)

        # Prepare email arguments
        email_args = {
            "recipients": recipients,
            "subject": rendered_subject,
            "message": rendered_email_content,
        }

        if sender_email:
            email_args["sender"] = sender_email

        # Send email
        frappe.sendmail(**email_args)

        return {"status": "Success", "message": "Email sent successfully."}
    except Exception as e:
        # Log any errors encountered while sending the email.
        frappe.log_error(
            message=f"Error sending generic email with context {context}: {str(e)}",
            title="Generic Email Send Error"
        )
        return {"status": "Failed", "message": f"Error encountered: {str(e)}"}
    
from frappe.utils.file_manager import save_file

@frappe.whitelist(allow_guest=True)
def request_form(**kwargs):

    config = Configurations()
    
    # Fetch sender email from Configurations or fallback to Email Account settings
    sender_email = config.get_no_reply_email()
    
    if not sender_email:
        sender_email = frappe.db.get_single_value("Email Account", "email_id")


    # Extract form data from the request
    form_data = dict(frappe.request.form)
    
    # Merge form_data into kwargs. This will allow form fields to override any matching kwargs, if necessary.
    kwargs.update(form_data)
    
    request_id = kwargs.get('request_id', '')

    email_template_name="request-form"

    # Check if the custom email template exists
    if frappe.db.exists("Email Template", f"custom-{email_template_name}"):
        email_template = frappe.get_doc("Email Template", f"custom-{email_template_name}")
    # Check if the specified email template exists
    elif frappe.db.exists("Email Template", email_template_name):
        email_template = frappe.get_doc("Email Template", email_template_name)
    else:
        default_email_templates = frappe.get_all("Email Template", limit=1)
        if not default_email_templates:
            return {"status": "Failed", "message": "No email template found."}
        email_template = frappe.get_doc("Email Template", default_email_templates[0].name)

    # Handle attachment data
    attachments_to_send = []
    if hasattr(frappe.request, 'files') and frappe.request.files:
        for file_key in frappe.request.files:
            uploaded_file = frappe.request.files[file_key]
            
            file_content = uploaded_file.stream.read()  # Read the content from the stream

            file_data = save_file(
                fname=uploaded_file.filename,
                content=file_content,  # passing the content as bytes
                dt="Email Template",
                dn=email_template.name,  
                is_private=0
            )

            attachments_to_send.append({
                "fname": file_data.file_name,
                "fcontent": file_content  # You may need to base64 encode this if the email sending function expects it
            })
    else:
        attachments_to_send = None

    # Spread kwargs into context and replace underscores with spaces
    query_args = {key.replace('_', ' '): value for key, value in kwargs.items() if key not in ('cmd')}
    # This is your string representation
    context_string = ''
    if query_args:
        context_string += '<br/>'.join([f'{key}={value}' for key, value in query_args.items()]) + '<br/>'

    config = Configurations()   
    email_b2b = config.get_email_b2b()
    recipient = kwargs.get('recipient', email_b2b)
    
    recipients = [recipient]

    context = {
        "context":context_string,
        "request_id":request_id,
        "data":kwargs
        # ... you can add other context variables as needed
    }
    try:
        # Render the email content with the context
        rendered_email_content = frappe.render_template(email_template.response_, context)
        rendered_subject = frappe.render_template(email_template.subject, context)

         # Prepare email arguments
        email_args = {
            "recipients": recipients,
            "subject": rendered_subject,
            "message": rendered_email_content,
            "attachments":attachments_to_send
        }

        if sender_email:
            email_args["sender"] = sender_email

        # Send email
        frappe.sendmail(**email_args)

        # Optionally, you can delete the saved files after sending the email if you no longer need them.
        # if isinstance(attachments_to_send, list):
        #     for file_data.file_url in attachments_to_send:
        #         file_doc = frappe.get_doc("File", {"file_url": file_data.file_url})
        #         file_doc.flags.ignore_permissions = True
        #         file_doc.delete()

        return {"status": "Success", "message": "Email inviata con successo."}
    except Exception as e:
        # Log the error
        frappe.log_error(message=f"Error sending sales order confirmation email for {context}: {str(e)}", title=f"Request Form  Email Error ")

        # Return a response indicating that there was an error
        return {"status": "Failed", "message": f"Error encountered: {str(e)}"}