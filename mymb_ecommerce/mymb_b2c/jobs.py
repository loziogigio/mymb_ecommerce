from mymb_ecommerce.mymb_b2c.product import import_all_products_from_mymb_b2c, start_import_mymb_b2c_from_external_db
from mymb_ecommerce.mymb_b2c.item import get_count_items_from_external_db, import_items_in_solr
from mymb_ecommerce.mymb_b2c.sales_order  import export_sales_order, close_and_submit_orderstatus
from mymb_ecommerce.mymb_b2c.feed_trova_prezzi  import init_feed_generation
from mymb_ecommerce.mymb_b2c.feed_google_merchant  import upload_to_google_merchant_create_product
from mymb_ecommerce.mymb_b2c.available_again  import action_job_process_available_again_email
from omnicommerce.controllers.email import send_sales_order_confirmation_email_html
import frappe
from mymb_ecommerce.mymb_b2c.settings.configurations import Configurations
import json

@frappe.whitelist(allow_guest=True, methods=['POST'])
def import_mymb_b2c_products():
    frappe.enqueue(import_all_products_from_mymb_b2c, batch_size=10, queue='short', timeout=600)
    return "import_all_products_from_mymb_b2c, batch_size=20, queue='short', timeout=600 is in progress"


@frappe.whitelist(allow_guest=True, methods=['POST'])
def update_solr(time_laps=None, filters=None, channel_id=None , total_item=None , batch_size=None , feature_channel_id='DEFAULT'):


    # total_item = get_count_items_from_external_db(time_laps=time_laps, filters=filters, channel_id=channel_id)
    if not total_item:
        total_item = get_count_items_from_external_db(time_laps=time_laps, filters=filters, channel_id=channel_id )
    
    # Define the batch size
    if not batch_size:
        batch_size = 100
    
    # Calculate total number of pages/batches
    total_pages = -(-total_item // batch_size)  # This is a neat trick for "ceiling division"
    
    # Enqueue each batch as a separate background job
    for page in range(1, total_pages + 1):
        frappe.enqueue(
            method=import_items_in_solr,
            limit=batch_size,
            page=page,
            time_laps=time_laps,
            filters=filters,
            fetch_property=True,
            fetch_media=True,
            fetch_price=True,
            fetch_categories=True,
            channel_id=channel_id,
            feature_channel_id=feature_channel_id,
            queue='short',
            timeout=600
        )
    
    return f"solr import {total_item} records are being imported in batches of {batch_size}. Jobs have been enqueued and are in progress."


@frappe.whitelist(allow_guest=True, methods=['POST'])
def update_omnicommerce(time_laps=None, filters=None, channel_id=None , total_item=None , batch_size=None):


    # total_item = get_count_items_from_external_db(time_laps=time_laps, filters=filters, channel_id=channel_id)
    if not total_item:
        total_item = get_count_items_from_external_db(time_laps=time_laps, filters=filters, channel_id=channel_id)
    
    # Define the batch size
    if not batch_size:
        batch_size = 100
    
    # Calculate total number of pages/batches
    total_pages = -(-total_item // batch_size)  # This is a neat trick for "ceiling division"
    
    # Enqueue each batch as a separate background job
    for page in range(1, total_pages + 1):
        frappe.enqueue(
            method=start_import_mymb_b2c_from_external_db,
            limit=batch_size,
            page=page,
            time_laps=time_laps,
            filters=filters,
            fetch_property=True,
            fetch_media=True,
            fetch_price=True,
            fetch_categories=True,
            channel_id=channel_id,
            queue='short',
            timeout=1200
        )
    
    return f"omnicommerce import {total_item} records are being imported in batches of {batch_size}. Jobs have been enqueued and are in progress."

@frappe.whitelist(allow_guest=True, methods=['POST'])
def job_export_sales_order(doc, method=None , sales_order_name=None):
    # Enqueue the job to run in the background
    config = Configurations()
    if config.enable_mymb_b2c:
        frappe.enqueue(method=export_sales_order,
                    doc=doc,
                    sales_order_name=sales_order_name,
                    queue='short',
                    timeout=240)  # Adjust the timeout as per your needs
        

@frappe.whitelist(allow_guest=True, methods=['POST'])
def job_emails_confirm_sales_order(doc=None, method=None, sales_order_name=None):
    # Enqueue the job to run in the background
    config = Configurations()
    email_b2c_bcc=None
    if(config.send_confirmation_email_to_admin):
        email_b2c_bcc = config.email_b2c

    # Fetch the sales_order if sales_order_name is provided
    if sales_order_name:
        sales_order = frappe.get_doc("Sales Order", sales_order_name)
    else:
        sales_order = doc

    if(sales_order.channel=="B2B"):
        return
    
    wire_info = ""
    email_template = config.confirm_sales_order_html_template

    # Change the template email if a transfer payment has been made
    if sales_order.payment_mode == "TRANSFER":
        wire_info = config.get_mymb_b2c_wire_transfer()
        email_template = config.confirm_sales_order_transfer_html_template
    if sales_order.payment_mode == "CASH_ON_DELIVERY":
        email_template = config.confirm_sales_order_cash_on_delivery_html_template

    if config.emails_confirm_sales_order_on_submit:
        frappe.enqueue(method=send_sales_order_confirmation_email_html,
                    sales_order=sales_order,
                    email_template=email_template,
                    bcc=email_b2c_bcc,
                    wire_info=wire_info,
                    queue='short',
                    timeout=240)  # Adjust the timeout as per your needs
    
    # Check if order has comments, then send them via email
    comments = frappe.get_all("Comment",
                              filters={"reference_name": sales_order.name,
                                       "reference_doctype": "Sales Order",
                                       "comment_type": "Comment"},
                              fields=["content"])
   
    if comments and config.email_b2c:
        # Combine all comments into a single string message
        comments_str = "\n\n".join([comment["content"] for comment in comments])
        frappe.sendmail(
            recipients=config.email_b2c,
            subject=f"Order Comments for {sales_order.name}",
            message=f"Comments for Sales Order {sales_order.name}:\n\n{comments_str}",
        )
        


@frappe.whitelist(allow_guest=True, methods=['POST'])
def job_export_feed_trova_prezzi_init(folder, file_name, feed_type, args=None, per_page=100 , max_item=None):
    # Enqueue the job to run in the background
    frappe.enqueue(method=init_feed_generation,
                    folder=folder,
                    file_name=file_name,
                    feed_type=feed_type,
                    args=args,
                    per_page=per_page,
                    max_item=max_item,
                    queue='default',
                    timeout=1200)  # Adjust the timeout as per your needs
    
@frappe.whitelist(allow_guest=True, methods=['POST'])
def job_export_feed_google_merchant_init(args, merchant_id, per_page, limit , credentials_json):
    # Enqueue the job to run in the background
    frappe.enqueue(method=upload_to_google_merchant_create_product,
                    merchant_id=merchant_id,
                    limit=limit,
                    per_page=per_page,
                    args=args,
                    credentials_json=credentials_json,
                    queue='default',
                    timeout=1200)  # Adjust the timeout as per your needs

@frappe.whitelist(allow_guest=True, methods=['POST'])
def job_export_feed_google_merchant_init(args, merchant_id, per_page, limit, credentials_json):
    # Convert args and credentials_json to serializable formats if they are not already
    serializable_args = json.dumps(args) if isinstance(args, dict) else args
    serializable_credentials = json.dumps(credentials_json) if isinstance(credentials_json, dict) else credentials_json

    # Enqueue the job to run in the background
    frappe.enqueue(method=upload_to_google_merchant_create_product,
                   merchant_id=merchant_id,
                   limit=limit,
                   per_page=per_page,
                   args=serializable_args,
                   credentials_json=serializable_credentials,
                   queue='default',
                   timeout=1200)  # Adjust the timeout as per your needs

@frappe.whitelist(allow_guest=True, methods=['POST'])
def job_update_order_from_mymb_to_erpnext(args=None):

    config = Configurations()
    if config.enable_mymb_b2c and args==None:
        order_shipped_label = config.order_shipped_label
        channel_id_lablel = config.channel_id_lablel
        sync_the_last_number_of_days = config.sync_the_last_number_of_days
        filters = {
            "channel_id":channel_id_lablel,
            "status":order_shipped_label
        }
        
        # Enqueue the job to run in the background
        frappe.enqueue(method=close_and_submit_orderstatus,
                    queue='default',
                    filters=filters, 
                    last_number_of_days=sync_the_last_number_of_days,
                    timeout=1200)  # Adjust the timeout as per your needs

@frappe.whitelist(allow_guest=True, methods=['POST'])
def job_process_available_again_email(args=None):
    try:
        # Parse args to get the email
        if args:
            args = json.loads(args)
            email = args.get('email')
        else:
            email = None
        
        # Enqueue the job to run in the background
        frappe.enqueue(method=action_job_process_available_again_email,
                       email=email,
                       queue='default',
                       timeout=1200)  # Adjust the timeout as per your needs

        return {"status": "Success", "message": "Job has been enqueued."}
    
    except Exception as e:
        frappe.log_error(message=str(e), title="Job Enqueue Error")
        return {"status": "Failed", "message": f"Error encountered: {str(e)}"}