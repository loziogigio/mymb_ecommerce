import frappe
from frappe import _
from frappe.utils import get_url
import urllib.parse
from frappe.utils import add_days, today, getdate
from datetime import date
import requests
import json
from frappe.utils.password import get_decrypted_password

from   payments.utils.utils import get_payment_gateway_controller
from   erpnext.accounts.doctype.payment_request.payment_request import get_party_bank_account,get_amount,get_dummy_message,get_existing_payment_request_amount,get_gateway_details,get_accounting_dimensions
from   payments.payment_gateways.doctype.paypal_settings.paypal_settings import get_redirect_uri, setup_redirect,update_integration_request_status,make_post_request,get_paypal_and_transaction_details
from mymb_ecommerce.mymb_b2c.settings.configurations import Configurations
from mymb_ecommerce.settings.configurations import Configurations as B2BConfigurations
from omnicommerce.controllers.email import send_sales_order_confirmation_email_html
from frappe.custom.doctype.property_setter.property_setter import make_property_setter
from payments.payment_gateways.doctype.paypal_settings.paypal_settings import PayPalSettings





@frappe.whitelist(allow_guest=True)
def create_address(**args):
    """Create a new address"""

    args = frappe._dict(args)
    customer = create_customer(args.customer_name, args.email)
    address = frappe.new_doc("Address")
    address.address_title = args.address_title
    address.address_type = args.address_type
    address.address_line1 = args.address_line1
    address.address_line2 = args.address_line2
    address.city = args.city
    address.state = args.state
    address.pincode = args.pincode
    address.phone = args.phone
    address.email_id = args.email
    address_links = {"customer": customer.name}
    address.links = frappe.as_json(address_links) # Convert dictionary to JSON string
    address.save(ignore_permissions=True)

    return {
        "address": address.as_dict()
    }

def create_customer(customer_name, email):
    customer = frappe.new_doc("Customer")
    customer.customer_name = customer_name
    customer.customer_group = "B2C"
    customer.email_id = email
    customer.territory = "All Territories"
    customer.insert(ignore_permissions=True)
    return customer


@frappe.whitelist(allow_guest=True)
def payment_request(quotation_name, payment_gateway="paypal"):
    quotation = frappe.get_doc("Quotation", quotation_name)

    if not quotation.grand_total:
        frappe.throw("Cannot create payment for a quotation with zero grand total.")

    sales_order = _create_sales_order(quotation , payment_gateway)

    doc = make_payment_request(dn=sales_order.name, dt="Sales Order", order_type="Shopping Cart", submit_doc=1)

    # Check the payment gateway and determine the appropriate URL
    wired_transfer_data = None
    clientSecret= None
    payment_url = None

    if payment_gateway == "stripe":
        clientSecret = get_stripe_secret(doc)
    elif payment_gateway == "paypal":
        payment_url = doc.get_payment_url()
    elif payment_gateway == "gestpay":
        payment_url = get_gestpay_url(doc)
    elif payment_gateway == "transfer":
        config = Configurations()
        payment_url = "/pages/payment-success?paymentgateway=transfer"
        submit_sales_order(sales_order.name)
        wired_transfer_data = f"{config.get_mymb_b2c_wire_transfer()}<h2>{sales_order.name}</h2>"
    elif payment_gateway == "cash_on_delivery":
        config = Configurations()
        payment_url = "/pages/payment-success?paymentgateway=cash_on_delivery"
        submit_sales_order(sales_order.name)
    else:
        payment_url = doc.get_default_url()  # Define this function to provide a default URL

    return {
        "payment_request": doc,
        "payment_url": payment_url,
        "wired_transfer_data" : wired_transfer_data,
        "clientSecret":clientSecret,
        "quotation":quotation
    }


@frappe.whitelist()
def submit_sales_order(sales_order_name):
    # Fetch the sales order by name or ID
    sales_order = frappe.get_doc("Sales Order", sales_order_name)
    
    # Bypass permissions
    sales_order.flags.ignore_permissions = True

    # Check if the sales order is in a state that allows submission
    if sales_order.docstatus == 0: # 0 means "Draft"
        sales_order.submit()
    else:
        frappe.throw(f"Sales Order {sales_order_name} is not in a 'Draft' state and cannot be submitted.")







def _create_sales_order(quotation, payment_gateway):
    # if quotation.status != "Draft":
    #     frappe.throw("Cannot create Sales Order for non-draft quotation.")

    items = []

    for quotation_item in quotation.items:
        item_dict = {
            "item_code": quotation_item.item_code,
            "item_name": quotation_item.item_name,
            "description": quotation_item.description,
            "qty": quotation_item.qty,
            "uom": quotation_item.uom,
            "rate": quotation_item.rate,
            "amount": quotation_item.amount,
            "price_list_rate": quotation_item.price_list_rate,
            # Add any other properties that you want to copy from the quotation item
        }
        items.append(item_dict)

    # Convert the payment gateway string to uppercase and check if it's in the allowed list
    payment_mode = payment_gateway.upper()
    allowed_payment_modes = ["PAYPAL", "TRANSFER", "STRIPE", "GESTPAY" , "CASH_ON_DELIVERY"]
    if payment_mode not in allowed_payment_modes:
        payment_mode="PAYPAL"
        frappe.throw(f"The payment mode {payment_mode} is not allowed. Please choose from {', '.join(allowed_payment_modes)}.")

    # customer_address_name, customer_address, shipping_address_name, shipping_address = get_quotation_addresses(quotation.name)
    order = frappe.get_doc({ 
        "doctype": "Sales Order",
        "naming_series": frappe.db.get_value("Selling Settings", None, "so_naming_series"),
        "customer": quotation.customer_name,
        "currency": quotation.currency,
        "items": items,
        "taxes": quotation.taxes,
        "payment_schedule": quotation.payment_schedule,
        "terms": quotation.terms,
        "shipping_address_name": quotation.shipping_address_name,
        "shipping_address": quotation.shipping_address,
        "customer_address": quotation.customer_address,
        "contact_person": quotation.contact_person,
        "contact_email": quotation.contact_email,
        "contact_mobile": quotation.contact_mobile,
        "party_name": quotation.customer_name,
        "delivery_date":  None,
        "order_type":"Shopping Cart",
        "selling_price_list": quotation.selling_price_list,
        "price_list_currency": quotation.price_list_currency,
        "plc_conversion_rate": quotation.plc_conversion_rate,
        "ignore_pricing_rule": quotation.ignore_pricing_rule,
        "total_qty": quotation.total_qty,
        "total_net_weight": quotation.total_net_weight,
        "base_total": quotation.base_total,
        "base_net_total": quotation.base_net_total,
        "total": quotation.total,
        "net_total": quotation.net_total,
        "tax_category": quotation.tax_category,
        "base_total_taxes_and_charges": quotation.base_total_taxes_and_charges,
        "total_taxes_and_charges": quotation.total_taxes_and_charges,
        "base_grand_total": quotation.base_grand_total,
        "base_rounding_adjustment": quotation.base_rounding_adjustment,
        "base_rounded_total": quotation.base_rounded_total,
        "base_in_words": quotation.base_in_words,
        "grand_total": quotation.grand_total,
        "rounding_adjustment": quotation.rounding_adjustment,
        "rounded_total": quotation.rounded_total,
        "in_words": quotation.in_words,
        "apply_discount_on": quotation.apply_discount_on,
        "base_discount_amount": quotation.base_discount_amount,
        "coupon_code": quotation.coupon_code,
        "additional_discount_percentage": quotation.additional_discount_percentage,
        "discount_amount": quotation.discount_amount,
        "payment_mode":payment_mode
    })

    # Update custom form field from quotation
    order.update({
        "quotation_name": quotation.name,
        "recipient_full_name": quotation.recipient_full_name,
        "recipient_email": quotation.recipient_email,
        "invoice_requested": quotation.invoice_requested,
        "channel": quotation.channel,
        "customer_type": quotation.customer_type
    });

    # Update custom form field from quotation based on customer type
    if quotation.customer_type == "Individual" and quotation.invoice_requested == "YES":
        order.update({"tax_code": quotation.tax_code})
    elif quotation.customer_type == "Company" and quotation.invoice_requested == "YES":
        order.update({
            "vat_number": quotation.vat_number,
            "company_name": quotation.company_name,
            "pec": quotation.pec,
            "client_id": quotation.client_id,
            "recipient_code": quotation.recipient_code
        })

    order.insert(ignore_permissions=True)

        # Fetch comments from the quotation
    quotation_comments = get_comments_for_quotation(quotation.name)
    
    # Add comments to the sales order, if any
    for comment in quotation_comments:
        frappe.get_doc({
            "doctype": "Comment",
            "comment_type": "Comment",
            "reference_doctype": "Sales Order",
            "reference_name": order.name,  # Assuming `order` is the variable holding the newly created Sales Order object
            "content": comment["content"],
            "comment_email": frappe.session.user
        }).insert(ignore_permissions=True)
        
    # order.submit()
    return order

def get_comments_for_quotation(quotation_name):
    comments = frappe.get_all("Comment",
                              filters={"reference_name": quotation_name,
                                       "reference_doctype": "Quotation",
                                       "comment_type": "Comment"},
                              fields=["name", "content"])
    return comments

def get_quotation_addresses(quotation_name):
    # Retrieve the Quotation document
    quotation = frappe.get_doc('Quotation', quotation_name)

    # Retrieve the names of the customer address and shipping address
    customer_address_name = quotation.customer_address
    shipping_address_name = quotation.shipping_address_name

    # Retrieve the Address documents
    customer_address = frappe.get_doc('Address', customer_address_name)
    shipping_address = frappe.get_doc('Address', shipping_address_name)


    return customer_address_name, customer_address, shipping_address_name, shipping_address

def get_gateway_details_like(gateway_name_substring: str) -> frappe._dict:
    """
    Retrieve payment gateway account whose name contains the given lowercase substring.
    """
    substring = gateway_name_substring.lower()

    all_accounts = frappe.get_all(
        "Payment Gateway Account",
        fields=["name", "payment_gateway", "payment_account", "payment_channel", "message"]
    )

    for account in all_accounts:
        if substring in account.get("payment_gateway", "").lower():
            return frappe._dict(account)

    frappe.throw(f"No Payment Gateway Account found matching '{substring}'.")


@frappe.whitelist(allow_guest=True)
def make_direct_guest_payment_request(amount, customer_email, payment_gateway="paypal", currency="EUR" , payment_channel="B2B" , customer_type="Company" , client_id=0 ,erp_document_numbe=0 , cancel_url=None):
    """
    Create a Sales Order for a guest user and use it as the reference to generate a Payment Request.
    """
    
    gateway_account = get_gateway_details_like(payment_gateway)

    if not gateway_account.get("name"):
        frappe.throw("Payment gateway configuration not found.")

    guest_customer = "Guest"
    company = frappe.defaults.get_user_default("Company")
    series_format = get_or_create_sales_order_series(payment_channel)

    # Ensure the service item exists
    item_code = get_or_create_guest_service_item(company)

    # Create Sales Order
    sales_order = frappe.get_doc({
        "doctype": "Sales Order",
        "naming_series": series_format,
        "customer": guest_customer,
        "currency": currency,
        "channel": payment_channel,
        "customer_type":customer_type,
        "client_id":client_id,
        "erp_document_number":erp_document_numbe,
        "delivery_date": frappe.utils.nowdate(),
        "transaction_date": frappe.utils.nowdate(),
        "items": [{
            "item_code": item_code,
            "qty": 1,
            "rate": amount
        }],
        "company": company
    }).insert(ignore_permissions=True)

    # sales_order.submit()

    # Create Payment Request using Sales Order
    pr = frappe.new_doc("Payment Request")
    pr.update({
        "payment_gateway_account": gateway_account.name,
        "payment_gateway": gateway_account.payment_gateway,
        "payment_account": gateway_account.payment_account,
        "payment_channel": gateway_account.get("payment_channel", "Email"),
        "payment_request_type": "Inward",
        "currency": currency,
        "grand_total": sales_order.grand_total,
        "mode_of_payment": gateway_account.mode_of_payment,
        "email_to": customer_email,
        "subject": f"Payment Request for Guest: {customer_email}",
        "message": f"Please complete your payment of {amount} {currency}.",
        "party_type": "Customer",
        "party": guest_customer,
        "reference_doctype": "Sales Order",
        "reference_name": sales_order.name,
    })

    pr.flags.mute_email = True
    pr.insert(ignore_permissions=True)
    pr.submit()

    # Determine payment method
    payment_url = None
    client_secret = None

    if payment_gateway == "stripe":
        client_secret = get_stripe_secret(pr)
    elif payment_gateway == "paypal":
        # payment_url = pr.get_payment_url()

        paypal = frappe.get_doc("PayPal Settings")
        payment_url = paypal.get_payment_url(
            amount=pr.grand_total,
            title=pr.subject,
            description=pr.message,
            reference_doctype=pr.doctype,
            reference_docname=pr.name,
            payer_email=pr.email_to,
            payer_name="Guest",
            order_id=pr.name,
            currency=pr.currency,
            payment_gateway=pr.payment_gateway,
            cancel_url=cancel_url # ✅ inject your cancel URL here
        )
    elif payment_gateway == "gestpay":
        payment_url = get_gestpay_url(pr)
    # elif payment_gateway == "transfer":
    #     config = Configurations()
    #     payment_url = "/pages/payment-success?paymentgateway=transfer"
    #     submit_sales_order(sales_order.name)
    #     wired_transfer_data = f"{config.get_mymb_b2b_wire_transfer()}<h2>{sales_order.name}</h2>"
    elif payment_gateway == "cash_on_delivery":
        config = Configurations()
        payment_url = "/pages/payment-success?paymentgateway=cash_on_delivery"
        submit_sales_order(sales_order.name)
    else:
        payment_url = pr.get_default_url()  # Define this function to provide a default URL

    return {
        "payment_request": pr.name,
        "payment_url": payment_url,
        "client_secret": client_secret,
        "reference": sales_order.name
    }


def get_or_create_guest_service_item(company):
    item_code = "GUEST-ITEM-SERVICE"

    if frappe.db.exists("Item", item_code):
        return item_code

    income_account = "Sales - " + frappe.get_cached_value("Company", company, "abbr")

    item = frappe.get_doc({
        "doctype": "Item",
        "item_code": item_code,
        "item_name": "Guest Payment Service",
        "description": "Service payment for guest checkout",
        "stock_uom": "Nos",
        "is_sales_item": 1,
        "is_stock_item": 0,
        "maintain_stock": 0,
        "disabled": 0,
        "item_group": "Services",
        "income_account": income_account
    }).insert(ignore_permissions=True)

    return item.item_code

def get_or_create_sales_order_series(payment_channel: str) -> str:
    """
    Ensure a naming series like 'B2B-.YY.-.#' exists and is set up correctly for Sales Order.
    """

    new_series = f"{payment_channel.upper()}-.YY.-.#"

    # Load existing options from metadata
    meta = frappe.get_meta("Sales Order")
    field = meta.get_field("naming_series")
    existing_options = field.options.split("\n") if field and field.options else []

    if new_series not in existing_options:
        updated_options = existing_options + [new_series]

        # Update options
        make_property_setter("Sales Order", "naming_series", "options", "\n".join(updated_options), "Text")

        # Clear cache
        frappe.clear_cache(doctype="Sales Order")

    return new_series


@frappe.whitelist(allow_guest=True)
def make_payment_request(**args):
    """Make payment request"""

    args = frappe._dict(args)

    ref_doc = frappe.get_doc(args.dt, args.dn)
    gateway_account = get_gateway_details(args) or frappe._dict()
    

    grand_total = args.grand_total or get_amount(ref_doc, gateway_account.get("payment_account"))

    
    bank_account = (
        get_party_bank_account(args.get("party_type"), args.get("party"))
        if args.get("party_type")
        else ""
    )

    draft_payment_request = frappe.db.get_value(
        "Payment Request",
        {"reference_doctype": args.dt, "reference_name": args.dn, "docstatus": 0},
    )

    existing_payment_request_amount = get_existing_payment_request_amount(args.dt, args.dn)

    if existing_payment_request_amount:
        grand_total -= existing_payment_request_amount

    # if draft_payment_request:
    if 1==2:
        frappe.db.set_value(
            "Payment Request", draft_payment_request, "grand_total", grand_total, update_modified=False
        )
        pr = frappe.get_doc("Payment Request", draft_payment_request)
    else:
        pr = frappe.new_doc("Payment Request")
        pr.update(
            {
                "payment_gateway_account": gateway_account.get("name"),
                "payment_gateway": gateway_account.get("payment_gateway"),
                "payment_account": gateway_account.get("payment_account"),
                "payment_channel": gateway_account.get("payment_channel"),
                "payment_request_type": args.get("payment_request_type"),
                "currency": ref_doc.currency,
                "grand_total": grand_total,
                "mode_of_payment": args.mode_of_payment,
                "email_to": args.recipient_id or ref_doc.owner,
                "subject": _("Payment Request for {0}").format(args.dn),
                "message": gateway_account.get("message") or get_dummy_message(ref_doc),
                "reference_doctype": args.dt,
                "reference_name": args.dn,
                "party_type": args.get("party_type") or "Customer",
                "party": args.get("party") or ref_doc.get("customer"),
                "bank_account": bank_account,
            }
        )

        # Update dimensions
        pr.update(
            {
                "cost_center": ref_doc.get("cost_center"),
                "project": ref_doc.get("project"),
            }
        )

        for dimension in get_accounting_dimensions():
            pr.update({dimension: ref_doc.get(dimension)})

        if args.order_type == "Shopping Cart" or args.mute_email:
            pr.flags.mute_email = True

        pr.insert(ignore_permissions=True)
        if args.submit_doc:
            pr.submit()

    return pr


def _convert_quotation_to_order(quotation_name):
    quotation = frappe.get_doc("Quotation", quotation_name)

    if quotation.status != "Draft":
        frappe.throw("Cannot convert a non-draft quotation to Sales Order.")


    quotation.status = "Ordered"
    quotation.save(ignore_permissions=True)

    return quotation

@frappe.whitelist(allow_guest=True)
def payment_result(payment_entry_name, status):
    payment_entry = frappe.get_doc("Payment Entry", payment_entry_name)

    if status == "success":
        order = _convert_quotation_to_order(payment_entry.reference_docname, payment_entry)

        payment_entry.reference_doctype = "Sales Order"
        payment_entry.reference_docname = order.name
        payment_entry.status = "Completed"
        payment_entry.save(ignore_permissions=True)

        frappe.msgprint("Payment successful. Sales Order {0} created.".format(order.name))
    else:
        payment_entry.status = "Failed"
        payment_entry.save(ignore_permissions=True)

        frappe.msgprint("Payment failed.")


def get_payment_url(payment_entry, payment_type, payment_settings):
    if payment_type == "paypal":
        return get_paypal_url(payment_entry, payment_settings)
    elif payment_type == "gestpay":
        return get_gestpay_url(payment_entry, payment_settings)
    else:
        frappe.throw(f"Invalid payment type: {payment_type}")

def get_paypal_url(payment_entry, paypal_settings):
    if not paypal_settings.api_username or not paypal_settings.api_password or not paypal_settings.signature:
        frappe.throw("PayPal is not configured.")

    paypal_url = "https://www.paypal.com/cgi-bin/webscr" if not paypal_settings.paypal_sandbox else "https://www.sandbox.paypal.com/cgi-bin/webscr"

    paypal_return_url = get_url("/payment-result?payment_entry_name=" + payment_entry.name + "&status=success")
    paypal_cancel_url = get_url("/payment-result?payment_entry_name=" + payment_entry.name + "&status=cancelled")

    paypal_params = {
        "cmd": "_xclick",
        "business": paypal_settings.api_username,
        "item_name": "Payment Entry " + payment_entry.name,
        "amount": payment_entry.paid_amount,
        "currency_code": payment_entry.paid_to_account_currency,
        "no_shipping": 1,
        "no_note": 1,
        "rm": 2,
        "notify_url": get_url("/api/method/frappe.integrations.doctype.paypal_settings.paypal_settings.notify_payment"),
        "return": paypal_return_url,
        "cancel_return": paypal_cancel_url
    }

    # return paypal_url + "?" + urllib.parse.urlencode(paypal_params)

def get_gestpay_url(doc):

    gestpay_settings = frappe.get_single('GestPay Settings')

    testEnv = gestpay_settings.test_environment
    shopLogin = gestpay_settings.shop_login
    transactionId = f"{doc.name}"
    item = f"N. Ord: {doc.reference_name}"
    amount = doc.grand_total

    # Define the API endpoint
    config = Configurations()
    gestpay_api_endpoint =  config.gestpay_api_endpoint

    api_url = f"{gestpay_api_endpoint}gestpay/pay"

    # Define the headers for the API request
    headers = {
        "Content-Type": "application/json"
    }

    # Define the payload for the API request
    payload = {
        "testEnv": testEnv,
        "shopLogin": shopLogin,
        "item": item,
        "amount": amount,
        "transactionId": transactionId
    }

    # Make the POST request and get the response
    response = requests.post(api_url, headers=headers, data=json.dumps(payload))

    # If the request was successful, return the URL
    if response.status_code == 200:
        return response.json()['url']  # Assuming the URL is returned in the 'url' key of the JSON response
    else:
        frappe.log_error(message=f"An error occurred while getting the Gestpay URL: {response.text}", title=f"Get Gestpay URL Error transactionID:{transactionId}")
        return None

def get_stripe_secret(doc):


    transactionId = f"{doc.name}"
    item = f"{doc.reference_name}"
    # stripe_key = 'sk_test_51NfwNVFoxMa9Ie1fdcT5BI2H5Ivqv7uzoOahzBbvpfT6jgvnY7HtlXrfcSxu0xrFWsL3if8281mQ9NL55cenTJbO00QvH2k3J2'
    amount = doc.grand_total

    # Fetch the stripe_key from Stripe Settings in ERPNext
    stripe_settings = frappe.get_all('Stripe Settings', limit_page_length=1)
    if stripe_settings:
        first_stripe_setting = frappe.get_doc('Stripe Settings', stripe_settings[0].name)
        # You can now use first_stripe_setting to access the fields
        publishable_key = first_stripe_setting.publishable_key
        stripe_key_encrypetd = first_stripe_setting.secret_key
        stripe_key = stripe_key = get_decrypted_password("Stripe Settings", first_stripe_setting.name, 'secret_key') # Decrypt the password


    # db_password = get_decrypted_password("Mymb Settings", self.doc.name, 'db_password')  # Decrypt the password
    config = Configurations()
    stripe_api_endpoint =  config.stripe_api_endpoint

    # Define the API endpoint
    api_url = f"{stripe_api_endpoint}stripe/create-payment-intent"

    # Define the headers for the API request
    headers = {
        "Content-Type": "application/json"
    }

    # Define the payload for the API request
    payload = {
        "amount": int(amount*100), #amount in cent
        "transactionId": item,
        "stripe_key":stripe_key
    }

    # Make the POST request and get the response
    response = requests.post(api_url, headers=headers, data=json.dumps(payload))

    # If the request was successful, return the clientSecret and update the Sales Order
    if response.status_code == 200:
        client_secret = response.json().get('clientSecret')
        custom_payment_code = response.json().get('id')

        # Update the Sales Order with the payment code
        sales_order = frappe.get_doc("Sales Order", doc.reference_name)
        sales_order.custom_payment_code = custom_payment_code
        sales_order.save()

        return client_secret
    else:
        frappe.log_error(message=f"An error occurred while getting the Gestpay URL: {response.text}", title=f"Get Gestpay URL Error transactionID:{transactionId}")
        return None


@frappe.whitelist(allow_guest=True, xss_safe=True)
def get_express_checkout_details(token):
    try:
        doc = frappe.get_doc("PayPal Settings")
        doc.setup_sandbox_env(token)

        params, url = doc.get_paypal_params_and_url()
        params.update({"METHOD": "GetExpressCheckoutDetails", "TOKEN": token})

        response = make_post_request(url, data=params)

        if response.get("ACK")[0] != "Success":
            frappe.respond_as_web_page(
                _("Something went wrong"),
                _(
                    "Looks like something went wrong during the transaction. Since we haven't confirmed the payment, Paypal will automatically refund you this amount. If it doesn't, please send us an email and mention the Correlation ID: {0}."
                ).format(response.get("CORRELATIONID", [None])[0]),
                indicator_color="red",
                http_status_code=frappe.ValidationError.http_status_code,
            )

            return

        doc = frappe.get_doc("Integration Request", token)
        update_integration_request_status(
            token,
            {"payerid": response.get("PAYERID")[0], "payer_email": response.get("EMAIL")[0]},
            "Authorized",
            doc=doc,
        )

        frappe.local.response["type"] = "redirect"
        frappe.local.response["location"] = get_redirect_uri(
            doc, token, response.get("PAYERID")[0]
        )

    except Exception:
        frappe.log_error(frappe.get_traceback())


@frappe.whitelist(allow_guest=True, xss_safe=True)
def confirm_payment(token):

    try:
        custom_redirect_to = None
        # Fetching PayPal and transaction details
        data, params, url = get_paypal_and_transaction_details(token)

        # Default values
        default_shop_name = "Default Shop"
        item_count = 0

        # Fetching shop name from settings
        mymb_b2c_settings = frappe.get_single('Mymb b2c Settings')
        shop_name = mymb_b2c_settings.b2c_title if mymb_b2c_settings and mymb_b2c_settings.b2c_title else default_shop_name

        # Fetching the Request Payment Name
        reference_docname = data.get("reference_docname")

        if reference_docname:
            # Fetch Sales Order from payment_request_id
            sales_order_name = frappe.get_doc("Payment Request", reference_docname).reference_name
            so = frappe.get_doc("Sales Order", sales_order_name)
            # Counting the number of items in the Sales Order
            item_count = so.total_qty if so else 0

        if so.channel == "B2B":
            config = B2BConfigurations()
            mymb_payment_success_page = config.get_mymb_payment_success_page()
            mymb_payment_failed_page = config.get_mymb_payment_failed_page()
            cart_number = so.erp_document_number
            description = f"Order {sales_order_name} / Cart. Number  {cart_number}" if reference_docname else f"Payment at {shop_name}"
        else:
            config = Configurations()
            mymb_payment_success_page = config.get_mymb_b2c_payment_success_page()
            mymb_payment_failed_page = config.get_mymb_b2c_payment_failed_page()
            # Build the description
            description = f"Order {sales_order_name} at {shop_name}, Product count: {item_count}" if reference_docname else f"Payment at {shop_name}"

        


        params.update(
            {
                "METHOD": "DoExpressCheckoutPayment",
                "PAYERID": data.get("payerid"),
                "TOKEN": token,
                "PAYMENTREQUEST_0_PAYMENTACTION": "SALE",
                "PAYMENTREQUEST_0_AMT": data.get("amount"),
                "PAYMENTREQUEST_0_CURRENCYCODE": data.get("currency").upper(),
                "PAYMENTREQUEST_0_DESC": description
            }
        )

        response = make_post_request(url, data=params)

        
        

        if response.get("ACK")[0] == "Success":
            _confirm_sales_order(payment_request_id=data.get("reference_docname") , status=response.get("ACK")[0] , payment_code=response.get("PAYMENTINFO_0_TRANSACTIONID")[0])
            update_integration_request_status(
                token,
                {
                    "transaction_id": response.get("PAYMENTINFO_0_TRANSACTIONID")[0],
                    "correlation_id": response.get("CORRELATIONID")[0],
                },
                "Completed",
            )

            if data.get("reference_doctype") and data.get("reference_docname"):
                try:
                    custom_redirect_to = frappe.get_doc(
                        data.get("reference_doctype"), data.get("reference_docname")
                    ).run_method("on_payment_authorized", "Completed")
                    frappe.db.commit()
                except Exception as e:
                    # Log the error, but continue execution
                    frappe.log_error(frappe.get_traceback(), title=str(e))

            
            redirect_url = "{}?doctype={}&docname={}".format(
                mymb_payment_success_page,data.get("reference_doctype"), data.get("reference_docname")
            )
        else:
            redirect_url = mymb_payment_failed_page

        setup_redirect(data, redirect_url )

    except Exception:
        frappe.log_error(frappe.get_traceback())

def _confirm_sales_order(payment_request_id=None, status='No', payment_code=None, sales_order_doc=None):
    # Fetch Sales Order from payment_request_id if not provided
    if not sales_order_doc:
        sales_order_doc = frappe.get_doc("Payment Request", payment_request_id).reference_name

    # Update Sales Order
    so = frappe.get_doc("Sales Order", sales_order_doc)

    so.transaction_date = frappe.utils.now_datetime()
    so.paid = 'YES' if status == "Success" else 'NO'
    so.payment_code = payment_code
    so.custom_payment_code = payment_code
    so.save(ignore_permissions=True)
    frappe.db.commit()
    so.submit()
    frappe.db.commit()



@frappe.whitelist(allow_guest=True, xss_safe=True)
def gestpay_transaction_result():
    gestpay_settings = frappe.get_single('GestPay Settings')

    testEnv = gestpay_settings.test_environment
     # db_password = get_decrypted_password("Mymb Settings", self.doc.name, 'db_password')  # Decrypt the password
    config = Configurations()
    gestpay_api_endpoint =  config.gestpay_api_endpoint
    
    
    try:
        # Define the API endpoint
        api_url = f"{gestpay_api_endpoint}gestpay/response"
        
         
        # Get the parameters from the original request
        parameters = frappe.request.args.to_dict()  # Convert ImmutableMultiDict to regular dictionary
        # Get the parameters from the original request
        parameters['testEnv'] = testEnv

        response = requests.get(api_url, params=parameters)


        # If the response is not successful, return
        if response.status_code != 200:
            return {"status": "Failed", "message": "Unable to fetch transaction result from server."}
        
        # Parse the response as json and transform it into a dictionary
        response_dict = frappe._dict(response.json())
        # Fetch 'data' from response_dict
        data = frappe._dict(response_dict.get('result', {}))
        
        # Get the ShopTransactionID and remove the 'brico-casa_' prefix
        payment_request_id = data.get("ShopTransactionID")

        # Fetch the related Payment Request Document
        payment_request_doc = frappe.get_doc("Payment Request", payment_request_id)

        # If the status is 'Requested', proceed to update the Payment Request
        if payment_request_doc.status == 'Requested' or 'Paid':
            # Check the TransactionResult to determine the status
            status = 'Success' if data.get("TransactionResult") == 'OK' else 'Failed'

            # Update Payment Request
            new_status = 'Paid' if status == "Success" else 'Failed'
            frappe.db.set_value("Payment Request", payment_request_id, "status", new_status)
            frappe.db.commit()  # Commit the transaction
            updated_payment_request_doc = frappe.get_doc("Payment Request", payment_request_id)

            # If payment was successful, confirm the sales order
            if updated_payment_request_doc.status == 'Paid':
                try:
                    _confirm_sales_order(payment_request_id=payment_request_id, status=status, payment_code=payment_request_id)
                    return {"status": "Success"}

                except Exception:
                    frappe.log_error(frappe.get_traceback())
                    return {"status": "Failed"}
            # If payment was unsuccessful, log the error
            else:
                error_msg = f"Failed: {payment_request_id} gest pay"
                frappe.log_error(message=data, title=error_msg)
                return {"status": "Failed"}
        else:
            # If the status is not 'Requested', do not make any changes and return a message
            return {"status": "Failed", "message": f"Payment Request status already updated'. No updates were made."}
        
    except Exception as e:
        error_msg = f"Failed: {payment_request_id} gestpay"
        frappe.log_error(message=f"request: {parameters} response: {data} error_message: {error_msg}", title=error_msg)
        return {"status": "Failed"}


@frappe.whitelist(allow_guest=True, xss_safe=True)
def gestpay_check_response():

    gestpay_settings = frappe.get_single('GestPay Settings')

    testEnv = gestpay_settings.test_environment
    
         # db_password = get_decrypted_password("Mymb Settings", self.doc.name, 'db_password')  # Decrypt the password
    config = Configurations()
    gestpay_api_endpoint =  config.gestpay_api_endpoint

    api_url = f"{gestpay_api_endpoint}gestpay/response"

    
    # Get the parameters from the original request
    parameters = frappe.request.args
    # parameters['testEnv'] = testEnv

    # Send GET request to api_url with parameters
    response = requests.get(api_url, params=parameters)

    # If the response is not successful, return
    if response.status_code != 200:
        return {"status": "Failed", "message": "Unable to fetch transaction result from server."}
    
     # Parse the response as json and transform it into a dictionary
    response_dict = frappe._dict(response.json())
    # Fetch 'data' from response_dict
    data = frappe._dict(response_dict.get('data', {}))

    # Get the ShopTransactionID and remove the 'brico-casa_' prefix
    payment_request_id = data.get("ShopTransactionID")

    # Fetch the related Payment Request Document
    payment_request_doc = frappe.get_doc("Payment Request", payment_request_id)

    if payment_request_doc.status == 'Paid':
        return {"status": "Success"}
    if payment_request_doc.status == 'Requested':
        return {"status": "In progress"}
    # If payment was unsuccessful, log the error
    else:
        error_msg = f"Failed: {payment_request_id} gest pay"
        frappe.log_error(message=data, title=error_msg)
        return {"status": "Failed"}
    
  

@frappe.whitelist(allow_guest=True, xss_safe=True)
def stripe_webhook():
    try:
        # Get the JSON data from the request
        event_data = frappe.request.get_data(as_text=True)
        event_json = json.loads(event_data)

        # Verify event type
        event_type = event_json.get('type')

        if event_type == "payment_intent.succeeded":
            # Extract payment intent details
            payment_intent = event_json.get('data', {}).get('object', {})
            payment_id = payment_intent.get('id')

            # Find the related Sales Order by custom_payment_code (which equals payment_id)
            sales_order = frappe.get_all('Sales Order', filters={'custom_payment_code': payment_id}, limit=1)
            
            if sales_order:
                sales_order_doc = sales_order[0].name
                so = frappe.get_doc("Sales Order", sales_order_doc)

                # Check if the Sales Order is already submitted
                if so.docstatus == 1:
                    return {"status": "Ignored", "message": f"Sales Order {sales_order_doc} is already submitted."}

    
                try:
                    # Confirm Sales Order
                    _confirm_sales_order( status="Success", sales_order_doc=sales_order_doc)
                    return {"status": "Success", "message": f"Payment succeeded for Sales Order {sales_order_doc}"}
                except Exception as e:
                    error_msg = f"Failed Payment Stripe: {payment_id} "
                    frappe.log_error(message=frappe.get_traceback(), title=error_msg)
                    return {"status": "Error", "message": f"Error confirming sales order for Payment ID: {payment_id}"}
            else:
                error_msg = f"Failed Payment Stripe: No Sales Order found for Payment ID {payment_id}"
                frappe.log_error(message=event_json, title=error_msg)
                return {"status": "Error", "message": f"No Sales Order found for Payment ID: {payment_id}"}
        else:
            return {"status": "Ignored", "message": "Event type not handled"}

    except Exception as e:
        error_msg = f"Failed Payment Stripe: General error"
        frappe.log_error(message=frappe.get_traceback(), title=error_msg)
        return {"status": "Error", "message": "An error occurred while processing the webhook"}


