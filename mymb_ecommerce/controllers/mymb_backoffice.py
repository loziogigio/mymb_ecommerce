
from mymb_ecommerce.utils.Media import Media
from mymb_ecommerce.settings.configurations import Configurations
from mymb_ecommerce.utils.Database import Database
import frappe
from frappe import _
from sqlalchemy import text
import json
from mymb_ecommerce.utils.Solr import Solr
from mymb_ecommerce.controllers.solr_crud import add_document_to_solr, update_document_in_solr
from slugify import slugify
import re
from mymb_ecommerce.repository.MyartmagRepository import MyartmagRepository

config = Configurations()
solr_instance = config.get_solr_instance(isSolrMymbBackoffice=True)
image_uri_instance = config.get_image_uri_instance()

# Update the update_categories function
@frappe.whitelist(allow_guest=True)
def ping():
    return {
        "data":"pong"
    }

@frappe.whitelist(allow_guest=True, methods=['POST'])
def get_mymartmag(limit=None, time_laps=None, page=1,  filters=None):
    # Initialize the BcartmagRepository
    item_repo = MyartmagRepository()

    # Fetch all the Bcartmag items from the external database
    items = item_repo.get_all_records(limit=limit,page=page, time_laps=time_laps, filters=filters, to_dict=True)

    return {
        "data": items
    }