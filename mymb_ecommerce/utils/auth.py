import datetime
import frappe
from frappe.utils.password import update_password
from frappe.utils import now_datetime, add_to_date
from frappe.utils.password import check_password
from frappe import _, msgprint




from mymb_ecommerce.utils.JWTManager import JWTManager, JWT_SECRET_KEY, JWT_EXPIRATION_DELTA
jwt_manager = JWTManager(secret_key=JWT_SECRET_KEY)

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

    # Create a JWT token for the new user
    token= create_jwt(user)

    return {
        "user": user.name,
        "customer": customer.name,
        "jwt": token
    }

@frappe.whitelist(allow_guest=True)
def sigin(usr, pwd):
    user = frappe.get_doc("User", usr)
    if user and check_password(user.name, pwd):
        token = create_jwt(user)
        return {
            "message": "Authentication successful",
            "jwt": token,
        }
    else:
        msgprint(_("Invalid login credentials"), raise_exception=True)

def create_jwt(user):
    payload = {
        'sub': user.name,
        'email': user.email,
        'roles': [role.role for role in user.get("roles")],
        'iat': now_datetime(),
    }
    token = jwt_manager.encode(payload, expiration_minutes=JWT_EXPIRATION_DELTA * 60)
    return token

#get user info with the linked customer
@frappe.whitelist(allow_guest=True)
@JWTManager.jwt_required
def get_user_info():
    # Get the user information from the JWT token payload
    jwt_payload = frappe.local.jwt_payload
    user_email = jwt_payload.get("email")

    user = frappe.get_doc("User", user_email)
    customer = frappe.get_doc("Customer", {"customer_name": user_email})

    return {
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "roles": [role.role for role in user.get("roles")],
        "customer": customer
    }

#update user firstname, lastname
@frappe.whitelist(allow_guest=True)
@JWTManager.jwt_required
def update_user_info( first_name=None, last_name=None):
    # Get the user information from the JWT token payload
    jwt_payload = frappe.local.jwt_payload
    user_email = jwt_payload.get("email")
    user = frappe.get_doc("User", user_email)

    if first_name:
        user.first_name = first_name
    if last_name:
        user.last_name = last_name

    user.save(ignore_permissions=True)

    return {
        "message": "User information updated successfully",
        "first_name": user.first_name,
        "last_name": user.last_name
    }

#update user password old_password, new_password
@frappe.whitelist(allow_guest=True)
@JWTManager.jwt_required
def update_user_password(user_email, old_password, new_password):
    # Get the user information from the JWT token payload
    jwt_payload = frappe.local.jwt_payload
    user_email = jwt_payload.get("email")
    user = frappe.get_doc("User", user_email)

    if check_password(user.name, old_password):
        update_password(user_email, new_password)
        return {
            "message": "Password updated successfully",
        }
    else:
        msgprint(_("Invalid old password"), raise_exception=True)


@frappe.whitelist(allow_guest=True)
@JWTManager.jwt_required
def me():
    # Get the user information from the JWT token payload
    jwt_payload = frappe.local.jwt_payload
    user_info = {
        "name": jwt_payload.get("sub"),
        "email": jwt_payload.get("email"),
        "roles": jwt_payload.get("roles", []),
        "iat":   datetime.datetime.fromtimestamp(jwt_payload.get("iat")).strftime('%Y-%m-%d %H:%M:%S')
        # Add other user fields as needed
    }
    return user_info
