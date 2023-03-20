from mymb_ecommerce.mymb_b2c.product import import_all_products_from_mymb_b2c
import frappe

@frappe.whitelist(allow_guest=True, methods=['POST'])
def import_mymb_b2c_products():
    frappe.enqueue(import_all_products_from_mymb_b2c, batch_size=10, queue='short', timeout=600)
    return "import_all_products_from_mymb_b2c, batch_size=20, queue='short', timeout=600 is in progress"
