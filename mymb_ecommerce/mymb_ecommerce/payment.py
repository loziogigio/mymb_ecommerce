import frappe
from frappe import _
from frappe.utils import get_url
import urllib.parse
from frappe.utils import add_days, today, getdate
from datetime import date
import requests
import json


from   payments.utils.utils import get_payment_gateway_controller
from   erpnext.accounts.doctype.payment_request.payment_request import get_party_bank_account,get_amount,get_dummy_message,get_existing_payment_request_amount,get_gateway_details,get_accounting_dimensions
from   payments.payment_gateways.doctype.paypal_settings.paypal_settings import get_redirect_uri, setup_redirect,update_integration_request_status,make_post_request,get_paypal_and_transaction_details
from mymb_ecommerce.mymb_b2c.settings.configurations import Configurations

config = Configurations()
mymb_b2c_payment_success_page = config.get_mymb_b2c_payment_success_page()
mymb_b2c_payment_failed_page = config.get_mymb_b2c_payment_failed_page()




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

    sales_order = _create_sales_order(quotation)

    doc = make_payment_request(dn=sales_order.name, dt="Sales Order", order_type="Shopping Cart", submit_doc=1)

    # Check the payment gateway and determine the appropriate URL
    wired_transfer_data = ""
    if payment_gateway == "paypal":
        payment_url = doc.get_payment_url()
    elif payment_gateway == "gestpay":
        payment_url = get_gestpay_url(doc)
    elif payment_gateway == "transfer":
        payment_url = "/pages/payment-success?paymentgateway=transfer"
        wired_transfer_data = "<p><strong>Si prega di effettuare il pagamento a:</strong><br>Intestatario: DEODATO S.R.L.<br>IBAN: IT27U0306904013100000011770<br>Banca: Intesa Sanpaolo<br>Filiale: Via Abate Gimma, 101, 70122 Bari BA<br><br>Inserire nella causale il numero d'ordine</p>"
    else:
        payment_url = doc.get_default_url()  # Define this function to provide a default URL

    return {
        "payment_request": doc,
        "payment_url": payment_url,
        "wired_transfer_data" : wired_transfer_data
    }

def _create_sales_order(quotation ):
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

	customer_address_name, customer_address, shipping_address_name, shipping_address = get_quotation_addresses(quotation.name)
	order = frappe.get_doc({ 
        "doctype": "Sales Order",
        "naming_series": frappe.db.get_value("Selling Settings", None, "so_naming_series"),
        "customer": quotation.customer_name,
        "currency": quotation.currency,
        "items": items,
        "taxes": quotation.taxes,
        "payment_schedule": quotation.payment_schedule,
        "terms": quotation.terms,
        "shipping_address_name": shipping_address_name,
        "shipping_address": shipping_address,
		"customer_address_name": customer_address_name,
        "customer_address": customer_address,
        "contact_person": quotation.contact_person,
        "contact_email": quotation.contact_email,
        "contact_mobile": quotation.contact_mobile,
        "party_name": quotation.customer_name,
        "delivery_date":  None,
		"order_type":"Shopping Cart",
        "discounts": 0
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
	# order.submit()
	return order

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

	if draft_payment_request:
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
    testEnv = True
    shopLogin = "GESPAY95439"
    transactionId = f"{doc.name}"
    item = f"brico-casa order {doc.reference_name}"
    amount = doc.grand_total

    # Define the API endpoint
    api_url = "https://crowdechain.com/gestpay/pay"

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
		data, params, url = get_paypal_and_transaction_details(token)

		params.update(
			{
				"METHOD": "DoExpressCheckoutPayment",
				"PAYERID": data.get("payerid"),
				"TOKEN": token,
				"PAYMENTREQUEST_0_PAYMENTACTION": "SALE",
				"PAYMENTREQUEST_0_AMT": data.get("amount"),
				"PAYMENTREQUEST_0_CURRENCYCODE": data.get("currency").upper(),
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
				custom_redirect_to = frappe.get_doc(
					data.get("reference_doctype"), data.get("reference_docname")
				).run_method("on_payment_authorized", "Completed")
				frappe.db.commit()
			
			redirect_url = "{}?doctype={}&docname={}".format(
				mymb_b2c_payment_success_page,data.get("reference_doctype"), data.get("reference_docname")
			)
		else:
			redirect_url = mymb_b2c_payment_failed_page

		setup_redirect(data, redirect_url )

	except Exception:
		frappe.log_error(frappe.get_traceback())

def _confirm_sales_order(payment_request_id, status, payment_code=None):
    # Fetch Sales Order from payment_request_id
    sales_order_doc = frappe.get_doc("Payment Request", payment_request_id).reference_name

    # Update Sales Order
    so = frappe.get_doc("Sales Order", sales_order_doc)

    so.transaction_date = frappe.utils.now_datetime()
    so.paid = 'YES' if status == "Success" else 'NO'
    so.payment_code = payment_code
    so.save(ignore_permissions=True)
    frappe.db.commit()
    so.submit()
    frappe.db.commit()
    # frappe.db.commit()
    # frappe.db.commit()  # Commit the transaction

    # Debugging step
    # updated_status = frappe.db.get_value("Sales Order", sales_order_doc, "order_status")  # Fetch the updated status
    # frappe.log_error(message=f"Updated order_status: {updated_status}", title="Debug Log")  

@frappe.whitelist(allow_guest=True, xss_safe=True)
def gestpay_transaction_result():
    
    
    # Define the API endpoint
    api_url = "https://crowdechain.com/gestpay/server/response"
    
    # Get the parameters from the original request
    parameters = frappe.request.args

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


@frappe.whitelist(allow_guest=True, xss_safe=True)
def gestpay_check_response():
    
    # Define the API endpoint
    api_url = "https://crowdechain.com/gestpay/server/response"
    
    # Get the parameters from the original request
    parameters = frappe.request.args

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