
import frappe
from datetime import datetime
from mymb_ecommerce.model.B2COrder import B2COrder
from mymb_ecommerce.model.B2COrderTransaction import B2COrderTransaction
from mymb_ecommerce.repository.B2COrderRepository import B2COrderRepository
from mymb_ecommerce.repository.B2COrderRowRepository import B2COrderRowRepository
from mymb_ecommerce.repository.B2COrderTransactionRepository import B2COrderTransactionRepository
from mymb_ecommerce.model.B2COrderRow import B2COrderRow

@frappe.whitelist(allow_guest=True, methods=['POST'])
def get_sales_order(limit=None, page=None, time_laps=None, filters=None):
    # Fetch Sales Orders
    sales_orders = frappe.get_all('Sales Order', fields=['*'], filters=filters, limit_page_length=limit, start=(page-1)*limit if page else 0)

    # Iterate through Sales Orders to get additional details
    for sales_order in sales_orders:
        # Fetch Sales Order Items
        sales_order['items'] = frappe.get_all('Sales Order Item', fields=['*'], filters={'parent': sales_order.name})
        
        # Fetch Payment Requests
        sales_order['payment_requests'] = frappe.get_all('Payment Request', fields=['*'], filters={'reference_name': sales_order.name})
         # Recover Addresses
        sales_order['billing_address_details'] = frappe.get_doc('Address', sales_order['customer_address']) if sales_order.get('customer_address') else None
        sales_order['shipping_address_details'] = frappe.get_doc('Address', sales_order['shipping_address_name']) if sales_order.get('shipping_address_name') else None


    return {
        "data": sales_orders
    }




@frappe.whitelist(allow_guest=True, methods=['POST'])
def export_new_sales_order(limit=None, page=None, time_laps=None, filters=None):
    # Fetch Sales Orders
    sales_orders = get_sales_order(limit, page, time_laps, filters)['data']

    # Instantiate B2COrderRepository
    b2c_order_repo = B2COrderRepository()

    # Iterate through Sales Orders to export to new schema
    for sales_order in sales_orders:
        billing_address_details = vars(sales_order.get('billing_address_details', None))
        shipping_address_details = vars(sales_order.get('shipping_address_details', None))
        order_rows =sales_order['items']
        order_transactions = sales_order['payment_requests']

        # Map fields from ERPNext Sales Order to B2COrder
        b2c_order = B2COrder(
            # existing fields here...
            external_ref=sales_order['name'],
            email=sales_order['recipient_email'],
            payment_method=sales_order['payment_mode'],
            status= 'PAID ', #sales_order['transaction_status'],
            currency=sales_order['currency'],
            total_amount=sales_order['total'],
            creation_date=datetime.now(), # You may need to adjust this based on your data

            
            billing_country=billing_address_details.get('country','IT'),
            billing_prov=billing_address_details.get('state','IT'),
            billing_city=billing_address_details.get('city',''),
            billing_address=billing_address_details.get('address_line1','')+' '+billing_address_details.get('address_line2',''),
            billing_postalcode=billing_address_details['pincode'],
            billing_name=billing_address_details['name'],
            billing_phone=billing_address_details['phone'],

            shipping_country=shipping_address_details.get('country','IT'),
            shipping_prov=shipping_address_details.get('state','IT'),
            shipping_city=shipping_address_details.get('city',''),
            shipping_address=shipping_address_details.get('address_line1','')+' '+shipping_address_details.get('address_line2',''),
            shipping_postalcode=shipping_address_details['pincode'],
            shipping_name=shipping_address_details['name'],
            shipping_phone=shipping_address_details['phone'],

            channel_id=sales_order['channel']
        )
        
        # Save the B2COrder
        b2c_order_repo.session.add(b2c_order)
        b2c_order_repo.session.commit()
        export_order_rows(b2c_order, order_rows)
        export_order_transactions(b2c_order,order_transactions[0])


    return {
        "status": "success",
        "message": f"{len(sales_orders)} sales orders exported successfully."
    }

def export_order_rows(b2c_order, line_items):
    # Assuming B2COrderRowRepository is your class to handle database interactions for order_rows
    b2c_order_row_repo = B2COrderRowRepository()

    # Initialize row number
    rn = 1

    # Iterate through line items
    for row in line_items:
        # Create order_row object with required details
        order_row = B2COrderRow(
            order_id= b2c_order.order_id ,
            row_id=row['idx'],
            row_num=rn,
            type='product',
            sku=row['item_code'],
            label=row['item_name'],
            quantity=row['qty'],
            currency=b2c_order.currency,
            total_amount=row['amount'],
            base_price=row['rate'],
            unit_amount=row['rate']
        )

        # Add order_row to the session
        b2c_order_row_repo.session.add(order_row)

        # Increment row number
        rn += 1

    # Commit the session to save all order rows
    b2c_order_row_repo.session.commit()

    return True

def export_order_transactions(b2c_order, order_transaction):
    # Assuming B2COrderTransactionRepository is your class to handle database interactions for order_transactions
    b2c_order_transaction_repo = B2COrderTransactionRepository()
    payload = None
    # Convert payment and status to a dictionary, and serialize them
    if payload is not None:
        payload = payload.encode('utf-8')
    # Create transaction object with required details
    transaction = B2COrderTransaction(
        transaction_id=order_transaction['name'],
        order_id= b2c_order.order_id ,
        status='PAID',
        currency=b2c_order.currency,
        amount=order_transaction['grand_total'],
        transaction_date=order_transaction['creation'],
        modify_date=order_transaction['modified'], # Make sure this is a valid datetime object
        remote_status='PAID',
        payload=payload
    )

    # Add transaction to the session
    b2c_order_transaction_repo.session.add(transaction)

    # Commit the session to save the transaction
    b2c_order_transaction_repo.session.commit()

    return True
