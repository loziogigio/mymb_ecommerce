from datetime import datetime, timedelta
import frappe
from frappe.utils.password import update_password
from frappe.utils import now_datetime, add_to_date
from frappe.utils.password import check_password, get_password_reset_limit
from frappe import _, msgprint
from frappe.rate_limiter import rate_limit
from mymb_ecommerce.mymb_b2c.settings.configurations import Configurations
import json


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
        'iat': datetime.utcnow() - timedelta(days=1)
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


from frappe.utils.data import sha256_hash
from frappe.core.doctype.user.user import User


@frappe.whitelist(allow_guest=True)
@rate_limit(limit=get_password_reset_limit, seconds=60 * 60)
# @rate_limit(limit=100, seconds=60 * 60)
def reset_password(user: str):
    try:
        user_doc = frappe.get_doc("User", user)
        
        # Check if the user is "Administrator" or if the user is disabled
        if user_doc.name == "Administrator":
            return {
                "status": "failed",
                "message": "Password reset not allowed for Administrator."
            }
        
        if not user_doc.enabled:
            return {
                "status": "failed",
                "message": "User account is disabled."
            }
        
        # Validate and send reset password email
        user_doc.validate_reset_password()
        user_reset_password(user_doc, send_email=True)

        return {
            "status": "success",
            "message": _("Password reset instructions have been sent to your email."),
            "title": _("Password Email Sent")
        }

    except frappe.DoesNotExistError:
        frappe.local.response["http_status_code"] = 404
        return {
            "status": "failed",
            "message": "User not found.",
            "http_status_code": 404
        }
    
    except Exception as e:
        # Log the error for debugging purposes
        frappe.log_error(message=str(e), title="Password Reset Error")

        # Return a generic error message
        return {
            "status": "failed",
            "message": "An error occurred during the password reset process.",
            "error": str(e)
        }
     
def user_reset_password( user ,  send_email=False, password_expired=False):
    config = Configurations()
    mymb_b2c_url = config.b2c_url

    key = frappe.generate_hash()
    hashed_key = sha256_hash(key)
    user.db_set("reset_password_key", hashed_key)
    user.db_set("last_reset_password_key_generated_on", now_datetime())

    

    url = "/pages/update-password?key=" + key
    if password_expired:
        url = "/pages/update-password?key=" + key + "&password_expired=true"

    link = mymb_b2c_url+url
    if send_email:
        auth_password_reset_mail(user.email, link)

    return link

def auth_password_reset_mail(user, link):
    """Send password reset email with a custom or default template.

    Args:
        user (str): The user's email or username.
        link (str): The password reset link.
    """

    # Check if the custom email template exists
    email_template_name = 'custom-reset-password-template'
    if frappe.db.exists("Email Template", email_template_name):
        email_template = frappe.get_doc("Email Template", email_template_name)
    # Else if the general email template exists by removing 'custom-'
    elif frappe.db.exists("Email Template", email_template_name.replace('custom-', '', 1)):
        email_template = frappe.get_doc("Email Template", email_template_name.replace('custom-', '', 1))
    # Use any available template as the last resort
    else:
        default_email_templates = frappe.get_all("Email Template", limit=1)
        if not default_email_templates:
            return {"status": "Failed", "message": "No email template found."}
        email_template = frappe.get_doc("Email Template", default_email_templates[0].name)

    # Prepare the email context
    email_context = {
        "link": link
    }

    try:
        # Render the email content and subject with the context
        rendered_email_content = frappe.render_template(email_template.response_, email_context)
        rendered_subject = frappe.render_template(email_template.subject, email_context)

        # Send the email
        frappe.sendmail(
            recipients=[user],
            subject=rendered_subject,
            message=rendered_email_content,
            now=True
        )

        return {"status": "Success", "message": "Password reset instructions have been sent to your email."}

    except Exception as e:
        # Log the error
        frappe.log_error(
            message=f"Error sending password reset email for user {user}: {str(e)}", 
            title=f"Password reset {user} email error"
        )

        # Return a response indicating that there was an error
        return {"status": "Failed", "message": f"Error encountered: {str(e)}"}

#update user password old_password, new_password and key
from frappe.core.doctype.user.user import _get_user_for_update_password, update_password as update_password_with_key 
@frappe.whitelist(allow_guest=True)
def update_user_password_with_key(new_password: str, key: str):
    """
    Update user's password using a reset key.
    
    Args:
        new_password (str): The new password to be set.
        key (str): The reset key for password recovery.
    """
    try:
        
        # Update the password using the reset key
        message = update_password_with_key(new_password=new_password, key=key)
        
        # Return a success message
        return {"status": "success", "message": message}
    
    except frappe.AuthenticationError as e:
        frappe.local.response["http_status_code"] = 401
        return {"status": "failed", "message": str(e)}
    
    except frappe.ValidationError as e:
        frappe.local.response["http_status_code"] = 400
        return {"status": "failed", "message": str(e)}
    
    except Exception as e:
        frappe.log_error(message=str(e), title="Password Update Error")
        frappe.local.response["http_status_code"] = 500
        return {"status": "failed", "message": _("An unexpected error occurred while updating the password.")}
    
