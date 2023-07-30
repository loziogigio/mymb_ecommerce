import frappe
from mymb_ecommerce.utils.JWTManager import JWTManager, JWT_SECRET_KEY
jwt_manager = JWTManager(secret_key=JWT_SECRET_KEY)


@frappe.whitelist(allow_guest=True)
@JWTManager.jwt_required
def add_to_wishlist(item_code):
    """Insert Item into wishlist."""

    user = frappe.local.jwt_payload['email']
    if frappe.db.exists("Wishlist Item", {"item_code": item_code, "parent": user}):
        return

    item_data = frappe.db.get_value(
        "Item",
        {"item_code": item_code},
        [
            "image",
            "name",
            "item_name",
            "item_group",
        ],
        as_dict=1,
    )

    if not item_data:
        return {"status": "error", "message": "Item not found"}

    wished_item_dict = {
        "item_code": item_code,
        "item_name": item_data.get("item_name"),
        "item_group": item_data.get("item_group"),
        "image": item_data.get("image")
    }

    if not frappe.db.exists("Wishlist", user):
        # initialise wishlist
        wishlist = frappe.get_doc({"doctype": "Wishlist"})
        wishlist.user = user
        wishlist.append("items", wished_item_dict)
        wishlist.save(ignore_permissions=True)
    else:
        wishlist = frappe.get_doc("Wishlist", user)
        item = wishlist.append("items", wished_item_dict)
        item.db_insert()


@frappe.whitelist(allow_guest=True)
@JWTManager.jwt_required
def remove_from_wishlist(item_code):
	user = frappe.local.jwt_payload['email']
	if frappe.db.exists("Wishlist Item", {"item_code": item_code, "parent": user}):
		frappe.db.delete("Wishlist Item", {"item_code": item_code, "parent": user})
		frappe.db.commit()  # nosemgrep
		wishlist_items = frappe.db.get_values("Wishlist Item", filters={"parent": user})
		return {"status": "success"}
	else:
		return {"status": "error"}


@frappe.whitelist(allow_guest=True)
@JWTManager.jwt_required
def get_from_wishlist(item_code=None, page=1, per_page=20 , user=None):
    if not user:
        user = frappe.local.jwt_payload['email']

    filters = {"parent": user}
    if item_code:
        filters["item_code"] = item_code

    # Convert the page and per_page values to integers
    page = int(page)
    per_page = int(per_page)

    start = (page - 1) * per_page
    wishlist_items = frappe.get_list("Wishlist Item",
        filters=filters,
        start=start,
		fields=['item_code'],
        page_length=per_page ,
	    ignore_permissions=True
    )

    if wishlist_items:
        return wishlist_items
    else:
        return None
