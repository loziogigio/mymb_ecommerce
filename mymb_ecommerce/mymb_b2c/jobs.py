from mymb_ecommerce.mymb_b2c.product import import_all_products_from_mymb_b2c
from mymb_ecommerce.controllers.solr_action import update_all_solr_category
import frappe

@frappe.whitelist(allow_guest=True, methods=['POST'])
def import_mymb_b2c_products():
    frappe.enqueue(import_all_products_from_mymb_b2c, batch_size=10, queue='short', timeout=600)
    return "import_all_products_from_mymb_b2c, batch_size=20, queue='short', timeout=600 is in progress"

@frappe.whitelist(allow_guest=True, methods=['POST'])
def update_all_solr_b2c_categories():
    frappe.enqueue(update_all_solr_category, queue='short')
    return "update_all_solr_b2c_categories,  queue=short is in progress"
