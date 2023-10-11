# from typing import Dict

import frappe
from frappe import _
# from frappe.utils.nestedset import get_root_of


@frappe.whitelist(allow_guest=True, methods=['POST'])
def set_search_settings(customer_code=None, customer_address_code=None, disable_gross_price_view=None , disable_autocomplete=None):
    # Ensure the required parameters are provided
    if not customer_code or not customer_address_code or disable_gross_price_view not in [True, False] or disable_autocomplete not in [True, False]:
        return {
            "data": _("Customer code, Customer address code, disable_gross_price_view, disable_autocomplete are mandatory.")
        }

    # Fetch the existing record, if any
    existing_record = frappe.get_value("Customer Search Settings",
                                       {"customer_code": customer_code, "customer_address_code": customer_address_code},
                                       ['name', 'customer_code','customer_address_code','disable_gross_price_view','admin_disable_gross_price_view', 'disable_autocomplete'],
                                       as_dict=True)

    # If the record doesn't exist, create a new one
    if not existing_record:
        new_record = frappe.get_doc({
            "doctype": "Customer Search Settings",
            "customer_code": customer_code,
            "customer_address_code": customer_address_code,
            "disable_gross_price_view": disable_gross_price_view,
            "disable_autocomplete": disable_autocomplete
        })
        new_record.insert(ignore_permissions=True)
        frappe.db.commit()
        data = _("New settings created successfully!")

    # If the record exists and admin_disable_gross_price_view is not True, update it
    else:
        if not existing_record.admin_disable_gross_price_view:
            frappe.db.set_value("Customer Search Settings", existing_record.name, {
                "disable_gross_price_view": disable_gross_price_view,
                "disable_autocomplete": disable_autocomplete
            })
            frappe.db.commit()
            data = _("Settings updated successfully!")
        else:
            data = _("Settings cannot be updated as admin has disabled gross price view.")

    return {
        "data": data
    }





@frappe.whitelist(allow_guest=True, methods=['GET'])
def get_search_settings(customer_code, customer_address_code):
    if not customer_code or not customer_address_code:
        return {
            "data": {
                "error": _("Customer code and Customer address code are mandatory.")
            }
        }

    # Fetch the existing record
    existing_record = frappe.get_value("Customer Search Settings",
                                       {"customer_code": customer_code, "customer_address_code": customer_address_code},
                                       ['name', 'customer_code','customer_address_code','disable_gross_price_view','admin_disable_gross_price_view' , 'disable_autocomplete'],
                                       as_dict=True)
    
    # Return the existing record if found, or default values
    if existing_record:
        admin_disable_gross_price_view = bool(existing_record.get("admin_disable_gross_price_view", False))
        disable_gross_price_view = True if admin_disable_gross_price_view else bool(existing_record.get("disable_gross_price_view", False))
        return {
            "data": {
                "name": existing_record.get("name"),
                "customer_code": customer_code,  # Use provided input value
                "customer_address_code": customer_address_code,  # Use provided input value
                "disable_gross_price_view": disable_gross_price_view,
                "admin_disable_gross_price_view": admin_disable_gross_price_view,
                "disable_autocomplete":  existing_record.get("disable_autocomplete")
            }
        }
    else:
        default_values = {
            "customer_code": customer_code,
            "customer_address_code": customer_address_code,
            "disable_gross_price_view": False,
            "admin_disable_gross_price_view": False,
            "disable_autocomplete":  False
        }
        return {
            "message": {
                "data": default_values
            }
        }

