import frappe
from frappe import _
from mymb_ecommerce.mymb_b2c.price_check import check_if_any_promotion
@frappe.whitelist(allow_guest=True)
def apply_coupon_code(quotation_name, applied_code, applied_referral_sales_partner):
    coupon_description = ""
    try:
        
        if not applied_code:
            frappe.throw(_("Please enter a coupon code"))

        coupon_list = frappe.get_all("Coupon Code", filters={"coupon_code": applied_code}, fields=["name", "custom_maximum_use_per_email" , "description"])
        if not coupon_list:
            frappe.throw(_("Please enter a valid coupon code"))

        coupon = coupon_list[0]
        coupon_description = coupon.get("description", "")

        from erpnext.accounts.doctype.pricing_rule.utils import validate_coupon_code

        validate_coupon_code(coupon["name"])

        quotation = frappe.get_doc("Quotation", quotation_name)

        
        items = quotation.get("items", None)
        # check if  any promotion, we delete the promo
         # Check if any promotion exists
        is_there_promo = check_if_any_promotion(items)

        if is_there_promo:
            # If there is a promotion, return a message
            response = {
                "status": "error",
                "message": "Il Coupon non e' cumulabile con altri sconti",
                "coupon_description": "<span class='text-danger fw-bolder'>Il Coupon non e' cumulabile con altri sconti</span> " +coupon_description
            }
            return response
        

        # Implement logic to check coupon usage limit per email
        if coupon.get("custom_maximum_use_per_email", 0) > 0:
            past_usage_count = frappe.db.count("Sales Order", filters={
                "recipient_email": quotation.recipient_email,  
                "coupon_code": coupon["name"],
                "docstatus": 1  # Only consider submitted sales orders
            })

            if past_usage_count >= coupon["custom_maximum_use_per_email"]:
                frappe.throw(_("This coupon code has been used the maximum number of times allowed."))

        quotation.coupon_code = coupon["name"]
        quotation.flags.ignore_permissions = True
        quotation.save()

        if applied_referral_sales_partner:
            sales_partner_list = frappe.get_all(
                "Sales Partner", filters={"referral_code": applied_referral_sales_partner}
            )
            if sales_partner_list:
                sales_partner_name = sales_partner_list[0].name
                quotation.referral_sales_partner = sales_partner_name
                quotation.flags.ignore_permissions = True
                quotation.save()


        # Convert quotation to a dictionary
        quotation_dict = quotation.as_dict()
        # Add coupon_description to the dictionary
        quotation_dict["coupon_description"] = coupon_description

        # Return the modified dictionary
        return quotation_dict

    except Exception as e:
        # Log the error
        frappe.log_error(str(e), "Error applying coupon code")

        # Return an error response
        response = {
            "status": "error",
            "message": str(e),
            "coupon_description":coupon_description
        }
        return response
