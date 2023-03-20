import frappe
from payments.utils.utils import get_payment_gateway_controller

@frappe.whitelist(allow_guest=True)
def create_quotation(items, customer_id=None, contact_info=None, shipping_address_different=False):

    # Fetch the customer from request
    if not customer_id:
        customer_id = "Guest"

    # Check if the customer already exists in the database
    customer = frappe.get_doc('Customer', customer_id)

    if not customer:
        # Create a new Customer document if it does not exist
        customer = frappe.new_doc('Customer')
        customer.customer_type = "Individual"
        customer.insert(ignore_permissions=True)

    # Create a new Quotation document
    quotation = frappe.get_doc({
        'doctype': 'Quotation',
        'party_name': customer.customer_name,
        'items': items
    })

    if contact_info:
        # Create a new Contact document and link it to the Customer document
        # contact = _create_contact(customer, contact_info)

        # Create new Address documents and link them to the Contact document
        billing_address = _create_address(customer, contact_info, address_type='Billing')

        if shipping_address_different:
            shipping_address = _create_address(customer, contact_info, address_type='Shipping')
        else:
            # Use the same address as the billing address if shipping address is not different
            shipping_address = billing_address


        # Set the billing and shipping addresses of the Quotation document
        quotation.customer_address = billing_address.name
        quotation.shipping_address_name = shipping_address.name

    # Save the Quotation document as a draft
    quotation.insert(ignore_permissions=True)

    # Return the Quotation document ID
    return quotation.name

def _create_contact(customer, contact_info):
    # Create a new Contact document
    contact = frappe.new_doc('Contact')
    contact.update({
        'first_name': contact_info.get('first_name'),
        'last_name': contact_info.get('last_name'),
        'email_id': contact_info.get('email'),
        'mobile_no': contact_info.get('mobile' , None),
        'customer': customer.name
    })

    # Save the Contact document
    contact.insert(ignore_permissions=True)

    # Link the Contact document to the Customer document
    customer.append('contacts', {
        'contact': contact.name
    })
    customer.save(ignore_permissions=True)

    return contact

def _create_address(customer, contact_info, address_type='Billing'):
    # Create a new Address document
    address = frappe.new_doc('Address')

    if address_type == 'Shipping':
        address_info = contact_info.get('shipping_address')
    else :
        address_info = contact_info.get('billing_address')

    address.update({
        'address_title': contact_info.get('name'),
        'email_id': contact_info.get('email_id'),
        'phone': contact_info.get('phone'),
        'address_line1': address_info.get('address_line1'),
        'address_line2': address_info.get('address_line2'),
        'city': address_info.get('city'),
        'state': address_info.get('state'),
        'pincode': address_info.get('pincode'),
        'country': address_info.get('country'),
        'address_type':address_type,
        'is_primary_address': False,
        'links': [{
            'link_doctype': 'Customer',
            'link_name': customer.name,
            'link_title': contact_info.get('name'),
        }]
    })

    

    # Save the Address document
    address.insert(ignore_permissions=True)


    return address


@frappe.whitelist(allow_guest=True)
def create_customer(same_address=True, **params):
    # use same address for shipping and billing if same_address is True
    if same_address:
        billing_address = params.get("address")
        shipping_address = params.get("address")
    else:
        billing_address = params.get("billing_address")
        shipping_address = params.get("shipping_address")

    customer = frappe.get_doc({
        "doctype": "Customer",
        "owner": "Guest",
        "customer_name": params.get("customer_name"),
        "customer_type": params.get("customer_type"),
        "gender": params.get("gender"),
        "email_id": params.get("email_id"),
        "mobile_no": params.get("mobile_no"),
        "customer_group": params.get("customer_group"),
        "territory": params.get("territory"),
        "billing_address": billing_address,
        "shipping_address_name": params.get("shipping_address_name"),
        "shipping_address": shipping_address,
    })

    customer.insert(ignore_permissions=True)
    return customer

@frappe.whitelist(allow_guest=True)
def connect_quotation_to_sales_order(quotation_id, sales_order_id):
    # Get the Quotation and Sales Order documents
    quotation = frappe.get_doc('Quotation', quotation_id)
    sales_order = frappe.get_doc('Sales Order', sales_order_id)

    # Submit the Quotation
    quotation.submit()

    # Connect the Quotation to the Sales Order
    sales_order.append('items', {
        'item_code': quotation.name,
        'item_name': quotation.name,
        'description': 'Quotation ' + quotation.name,
        'qty': 1,
        'rate': quotation.grand_total,
        'amount': quotation.grand_total
    })
    sales_order.save(ignore_permissions=True)

    # Return success message
    return 'Quotation {0} connected to Sales Order {1}'.format(quotation_id, sales_order_id)
