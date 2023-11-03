from mymb_ecommerce.mymb_b2c.product import import_all_products_from_mymb_b2c, start_import_mymb_b2c_from_external_db
from mymb_ecommerce.mymb_b2c.item import get_count_items_from_external_db, import_items_in_solr
from mymb_ecommerce.mymb_b2c.sales_order  import export_sales_order
import frappe
from mymb_ecommerce.mymb_b2c.settings.configurations import Configurations

@frappe.whitelist(allow_guest=True, methods=['POST'])
def import_mymb_b2c_products():
    frappe.enqueue(import_all_products_from_mymb_b2c, batch_size=10, queue='short', timeout=600)
    return "import_all_products_from_mymb_b2c, batch_size=20, queue='short', timeout=600 is in progress"


@frappe.whitelist(allow_guest=True, methods=['POST'])
def update_solr(time_laps=None, filters=None, channel_id=None , total_item=None , batch_size=None):


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