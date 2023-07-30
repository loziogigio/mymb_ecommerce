# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from datetime import datetime
import frappe

import frappe
from frappe import _
from frappe.contacts.doctype.contact.contact import get_contact_name
from frappe.model.document import Document
from frappe.utils import cint, flt

from erpnext.e_commerce.doctype.e_commerce_settings.e_commerce_settings import (
	get_shopping_cart_settings,
)

from mymb_ecommerce.utils.JWTManager import JWTManager, JWT_SECRET_KEY
jwt_manager = JWTManager(secret_key=JWT_SECRET_KEY)

class UnverifiedReviewer(frappe.ValidationError):
	pass


class ItemReview(Document):
	def after_insert(self):
		# regenerate cache on review creation
		reviews_dict = get_queried_reviews(self.website_item)
		set_reviews_in_cache(self.website_item, reviews_dict)

	def after_delete(self):
		# regenerate cache on review deletion
		reviews_dict = get_queried_reviews(self.website_item)
		set_reviews_in_cache(self.website_item, reviews_dict)


@frappe.whitelist(allow_guest=True)
def get_item_reviews(item_code, start=0, end=10, data=None):
	"Get Website Item Review Data."
	start, end = cint(start), cint(end)
	settings = get_shopping_cart_settings()

	# Get cached reviews for first page (start=0)
	# avoid cache when page is different
	from_cache = not bool(start)

	if not data:
		data = frappe._dict()

	if settings and settings.get("enable_reviews"):
		reviews_cache = frappe.cache().hget("item_reviews", item_code)
		if from_cache and reviews_cache:
			data = reviews_cache
		else:
			data = get_queried_reviews(item_code, start, end, data)
			if from_cache:
				set_reviews_in_cache(item_code, data)

	return data


def get_queried_reviews(item_code, start=0, end=10, data=None):
	"""
	Query Website Item wise reviews and cache if needed.
	Cache stores only first page of reviews i.e. 10 reviews maximum.
	Returns:
	        dict: Containing reviews, average ratings, % of reviews per rating and total reviews.
	"""
	if not data:
		data = frappe._dict()

	data.reviews = frappe.db.get_all(
		"Item Review",
		filters={"item": item_code},
		fields=['name','item' , 'customer' ,'rating','review_title as title','comment'],
		limit_start=start,
		limit_page_length=end,
	)

	rating_data = frappe.db.get_all(
		"Item Review",
		filters={"item": item_code},
		fields=["avg(rating) as average, count(*) as total"],
	)[0]

	data.average_rating = flt(rating_data.average, 1)
	data.average_whole_rating = flt(data.average_rating, 0)

	# get % of reviews per rating
	reviews_per_rating = []
	for i in range(1, 6):
		count = frappe.db.get_all(
			"Item Review", filters={"item": item_code, "rating": i}, fields=["count(*) as count"]
		)[0].count

		percent = flt((count / rating_data.total or 1) * 100, 0) if count else 0
		reviews_per_rating.append(percent)

	data.reviews_per_rating = reviews_per_rating
	data.total_reviews = rating_data.total

	return data


def set_reviews_in_cache(item_code, reviews_dict):
	frappe.cache().hset("item_reviews", item_code, reviews_dict)


@frappe.whitelist(allow_guest=True)
@JWTManager.jwt_required
def add_item_review(item_code, title, rating, comment=None):
	"""Add an Item Review by a user if non-existent."""
	user = frappe.local.jwt_payload['email']

	if not frappe.db.exists("Item Review", {"user": user, "item": item_code}):
		doc = frappe.get_doc(
			{
				"doctype": "Item Review",
				"user": user,
				"customer": get_customer(user=user , silent=True),
				"item": item_code,
				"website_item": item_code,
				"review_title": title,
				"rating": rating,
				"comment": comment,
			}
		)
		doc.published_on = datetime.today().strftime("%d %B %Y")
		doc.insert(ignore_permissions=True)

		# Update cache after adding the review
		reviews_dict = get_queried_reviews(item_code)
		set_reviews_in_cache(item_code, reviews_dict)


@frappe.whitelist(allow_guest=True)
@JWTManager.jwt_required
def delete_item_review(item_code):
    """Delete an Item Review by a user if they are the owner."""
    user = frappe.local.jwt_payload['email']
    item_review = frappe.db.exists("Item Review", {"user": user, "item": item_code})

    if item_review:
        doc = frappe.get_doc("Item Review", item_review)
        doc.delete(ignore_permissions=True)
        frappe.db.commit()

        # Update cache after deleting the review
        reviews_dict = get_queried_reviews(item_code)
        set_reviews_in_cache(item_code, reviews_dict)

        return {"status": "success", "message": "Item review deleted successfully."}
    else:
        return {"status": "error", "message": "You do not have permission to delete this review."}


def get_customer(user , silent=False ):
	"""
	silent: Return customer if exists else return nothing. Dont throw error.
	"""

	contact_name = get_contact_name(user)
	customer = None

	if contact_name:
		contact = frappe.get_doc("Contact", contact_name)
		for link in contact.links:
			if link.link_doctype == "Customer":
				customer = link.link_name
				break

	if customer:
		return frappe.db.get_value("Customer", customer)
	elif silent:
		return None
	else:
		# should not reach here unless via an API
		frappe.throw(
			_("You are not a verified customer yet. Please contact us to proceed."), exc=UnverifiedReviewer
		)
