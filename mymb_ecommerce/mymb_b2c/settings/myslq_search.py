

import json
from mymb_ecommerce.mymb_b2c.model.order import Order
from mymb_ecommerce.utils.Database import Database


import frappe
from frappe import _

solr = None
image_uri = None



@frappe.whitelist(allow_guest=True, methods=['GET'])
def get_mysql_instance():

    # Get the database configuration from the settings
    # db_config = frappe.get_doc('Mymb b2c Settings').as_dict()
    # Create a database instance
    db_config = {
    'drivername': 'mysql',
    'host': '161.156.172.254',
    'port': '33077',    
    'username': 'root',
    'password': 'z6GBW~s#',
    'database': 'bricocasa'
    }
    db = Database(db_config)

    # Define the page size and number
    page_size = 5
    page_number = 1

    # Calculate the offset
    offset = (page_number - 1) * page_size


    # Query the database using SQLAlchemy ORM
    query = db.session.query(Order).order_by(Order.order_id.desc()).offset(offset).limit(page_size)
    orders = query.all()

    # Convert each order object to JSON
    orders_json = [order.to_json() for order in orders]

    # Return the result as JSON
    return orders_json
