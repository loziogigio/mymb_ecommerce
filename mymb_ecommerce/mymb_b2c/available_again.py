
import frappe
from datetime import datetime
from frappe import _
from mymb_ecommerce.mymb_b2c.settings.configurations import Configurations
from mymb_ecommerce.mymb_b2c.product import start_import_mymb_b2c_from_external_db

@frappe.whitelist(allow_guest=True, methods=['POST'])
def add_record_to_available_again():

    #TODO: Validate customer and use email from customer jwt
    # Attempt to get the logged-in user's email from the JWT payload, if present
    user_email = frappe.local.jwt_payload.get('email') if hasattr(frappe.local, 'jwt_payload') else None

    # If there's a user email, try to fetch the linked Customer
    customer = frappe.db.get_value("Customer", {"name": user_email}, "name") if user_email else None

    # Get the request data
    data = frappe.local.form_dict

    try:
        # Check if the item exists in the database
        config = Configurations()
        # Ensure all items exist or import missing ones
        if not frappe.db.exists('Item', data.item_name) and config.enable_mymb_b2c:
            filters = {"carti": data.item_name}
            start_import_mymb_b2c_from_external_db(filters=filters, fetch_categories=True, fetch_media=True, fetch_price=True, fetch_property=True)
    except Exception as e:
        # Log the exception for debugging
        frappe.log_error(f"Error in creating website item: {e}")
        return {"status": "Failed", "message": f"An error occurred: {e}"}


    # Avoid replication: Check if a record with the same email and item already exists
    existing_record = frappe.db.exists("Available Again", {
        "email": user_email if user_email else data.email,
        "item_name": data.item_name
    })
    if existing_record:
        return {
            "error": "A record with this email and item already exists",
        }

    # If not found, use the 'Guest' customer
    if not customer:
        customer = frappe.db.get_value("Customer", {"name": "Guest"}, "name")
        if not customer:
            frappe.throw(_("Guest customer not found"))



    # Create a new AvailableAgain record
    new_record = frappe.get_doc({
        "doctype": "Available Again",
        "customer": customer,
        "email": user_email if user_email else data.email ,
        "item_name": data.item_name,
        "activation_time": data.activation_time or datetime.now(),  # Use current time if not provided
        "email_sent": data.get('email_sent', 0)  # Defaults to 0 (unchecked) if not provided
    })
    new_record.insert(ignore_permissions=True)

    # Commit to save the changes to the database
    frappe.db.commit()

    return {
        "message": "Record added successfully",
        "name": new_record.name  # Return the name (ID) of the created record
    }