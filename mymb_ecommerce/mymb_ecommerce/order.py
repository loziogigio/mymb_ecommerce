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
        billing_address = _create_address(customer, contact_info, address_type='Shipping')

        if shipping_address_different:
            shipping_address = _create_address(customer, contact_info, address_type='Billing')
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
def get_sales_orders_for_current_user():
    user = frappe.session.user
    sales_orders = frappe.get_list("Sales Order", filters={"owner": user})

    return sales_orders

import frappe

@frappe.whitelist()
def get_sales_orders_for_current_customer(page_num, page_size):
    user = frappe.session.user

    # Fetch the Customer linked to the current user using the "user" field
    customer = frappe.db.get_value("Customer", {"name": user}, "name")

    if not customer:
        return {"error": "No customer found for the current user"}

    # Calculate the offset based on the current page number and page size
    offset = (page_num - 1) * page_size

    # Fetch the Sales Orders related to the customer using a custom SQL query with pagination
    sales_orders = frappe.db.sql("""
        SELECT
            name,status,creation,modified, total, shipping_address, total_qty, address_display as billing_address
        FROM
            `tabSales Order`
        WHERE
            `tabSales Order`.`customer` = %s
        ORDER BY `tabSales Order`.`creation` DESC
        LIMIT %s OFFSET %s
    """, (customer, page_size, offset), as_dict=True)

        # Fetch the details for each item associated with each sales order
    for order in sales_orders:
        order_items = frappe.db.sql("""
            SELECT item_code, item_name, qty, rate, image
            FROM `tabSales Order Item`
            WHERE parent=%s
        """, order['name'], as_dict=True)
        order['items'] = order_items

    return sales_orders


@frappe.whitelist()
def get_sales_order_details(order_id):
    # Fetch the Sales Order using the provided order ID
    sales_order = frappe.get_doc("Sales Order", order_id)
    # Return an error message if the Sales Order is not found
    if not sales_order:
        return {"error": f"No Sales Order found with ID {order_id}"}

    # Verify that the current user is the owner of the Sales Order
    if not frappe.session.user == sales_order.customer:
        return {"error": "You do not have permission to access this Sales Order"}

    # Extract the relevant fields from the Sales Order document and return them as a dictionary
    return {
        "name": sales_order.name,
        # "customer": sales_order.customer,
        "status": sales_order.status,
        "total": sales_order.total,
        "items": [{"item_code": item.item_code,"item_name": item.item_name, "qty": item.qty, "rate": item.rate , "image": item.image } for item in sales_order.items]
    }
