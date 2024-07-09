
import frappe
from datetime import datetime
from frappe import _
from mymb_ecommerce.mymb_b2c.settings.configurations import Configurations
from mymb_ecommerce.mymb_b2c.product import start_import_mymb_b2c_from_external_db
from mymb_ecommerce.mymb_b2c.solr_search import catalogue

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


@frappe.whitelist(allow_guest=True, methods=['GET'])
def get_distinct_available_again_items(email=None):
    # Build the base query
    query = """
        SELECT item_name, COUNT(*) as item_count
        FROM `tabAvailable Again`
        WHERE email_sent = 0 AND item_name IS NOT NULL
    """
    
    # Add email filter if provided
    if email:
        query += " AND email = %s"
        params = (email,)
    else:
        params = ()
        
    query += " GROUP BY item_name"
    
    # Execute the query
    items = frappe.db.sql(query, params, as_dict=True)

    return {
        "message": "Items fetched successfully",
        "items": items  # Return the grouped items
    }

@frappe.whitelist(allow_guest=True, methods=['GET'])
def get_available_again_email(item_name, email=None):
    # Build the base query
    query = """
        SELECT DISTINCT email
        FROM `tabAvailable Again`
        WHERE email_sent = 0 AND item_name IS NOT NULL AND item_name = %s AND email IS NOT NULL
    """
    
    # Add email filter if provided
    if email:
        query += " AND email = %s"
        params = (item_name, email)
    else:
        params = (item_name,)
        
    # Execute the query
    emails = frappe.db.sql(query, params, as_dict=True)

    return {
        "message": "Emails fetched successfully",
        "emails": [email['email'] for email in emails]  # Return only the list of emails
    }


@frappe.whitelist(allow_guest=True, methods=['GET'])
def action_job_process_available_again_email(email=None):
    # Fetch all distinct items where email_sent is false
    distinct_items = get_distinct_available_again_items(email=email).get('items', [])

    log_messages = []

    for item in distinct_items:
        item_name = item['item_name']
        
        # Check if the item is in stock using the catalogue function
        args = {
            "is_in_stock": True,
            "skus": item_name
        }
        result = catalogue(args)
        products = result.get("products", [])

        if not products:
            log_messages.append(f"Item {item_name}: No products in stock")
            continue  # If there are no products in stock, skip to the next item

        # Fetch emails for the current item_name
        recipients = get_available_again_email(item_name, email=email).get("emails", [])

        if not recipients:
            log_messages.append(f"Item {item_name}: No recipients")
            continue  # If there are no recipients, skip to the next item

        # Send available again email
        email_status = send_available_again_email_html(item_name, recipients)

        if email_status.get("status") == "Success":
            # Update the records to mark email_sent as 1
            if email:
                frappe.db.sql("""
                    UPDATE `tabAvailable Again`
                    SET email_sent = 1
                    WHERE email_sent = 0 AND item_name = %s AND email = %s AND email IS NOT NULL
                """, (item_name, email))
            else:
                frappe.db.sql("""
                    UPDATE `tabAvailable Again`
                    SET email_sent = 1
                    WHERE email_sent = 0 AND item_name = %s AND email IS NOT NULL
                """, item_name)
            frappe.db.commit()
            log_messages.append(f"Item {item_name}: Successfully sent email to {len(recipients)} recipients ({', '.join(recipients)})")
        else:
            log_messages.append(f"Item {item_name}: Failed to send email")

    # Log the overall process
    # Get the current date and time
    current_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_message = "\n".join(log_messages)
    frappe.log_error(message=log_message, title=f"Available Again Email Process - {current_datetime}")

    return {"status": "Success", "message": "Processed available again emails for all items."}






@frappe.whitelist(allow_guest=True)
def send_available_again_email_html(item_name, recipients=None , email_template_name="custom-available-again-html" ):
    # Check if neither sales_order nor name is provided
    config = Configurations()
    b2c_url = config.b2c_url if config.b2c_url else 'https://www.omnicommerce.cloud'
    args= {
        "skus":item_name #is going to be the max number of item to procces
    }
    result = catalogue(args)
    products = result.get("products" , {})
    if not recipients:
        recipients = get_available_again_email(item_name).get("emails" , None)
    

    # Check if the custom email template exists
    if frappe.db.exists("Email Template", email_template_name):
        email_template = frappe.get_doc("Email Template", email_template_name)
    # else if the general email template exists by remove 'custom-'
    elif frappe.db.exists("Email Template",  email_template_name.replace('custom-', '', 1)):
        email_template = frappe.get_doc("Email Template",  email_template_name.replace('custom-', '', 1))
    else:
        default_email_templates = frappe.get_all("Email Template", limit=1)
        if not default_email_templates:
            return {"status": "Failed", "message": "No email template found."}
        email_template = frappe.get_doc("Email Template", default_email_templates[0].name)
        


    products = result.get("products" , {})
    context = {
        "product":products[0],
        "b2c_url":b2c_url
        # ... you can add other context variables as needed
    }
    try:
        # Render the email content with the context
        rendered_email_content = frappe.render_template(email_template.response_, context)
        rendered_subject = frappe.render_template(email_template.subject, context)

        # Send email
        frappe.sendmail(
            recipients=recipients,
            subject=rendered_subject,
            message=rendered_email_content
        )

        return {"status": "Success", "message": "Email sent successfully."}
    except Exception as e:
        # Log the error
        frappe.log_error(message=f"Error sending available again confirmation email for {item_name}: {str(e)}", title=f"Available Again {item_name} Email Error ")

        # Return a response indicating that there was an error
        return {"status": "Failed", "message": f"Error encountered: {str(e)}"}
