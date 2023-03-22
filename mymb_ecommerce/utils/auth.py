import frappe
from frappe.utils.password import update_password

@frappe.whitelist()
def create_customer_and_user(email, first_name, last_name, password):
    # Create a new user account with the "Customer" role

    user = frappe.get_doc({
        "doctype": "User",
        "email": email,
        "first_name": first_name,
        "last_name": last_name,
        "send_welcome_email": False,
        "roles": [
            {
                "role": "Customer"
            }
        ]
    })
    user.insert()

    # Reset the password after inserting the user
    update_password(email, password)


    # Create a new customer linked to the user account
    customer = frappe.get_doc({
        "doctype": "Customer",
        "customer_name": f"{email}",
        "customer_group": "B2C",
        "territory": "Italy",
        "customer_type": "Individual",
        "email_id": email,
        "mobile_no": "",
        "user": email
    })
    customer.insert()

    return {
        "user": user.name,
        "customer": customer.name
    }