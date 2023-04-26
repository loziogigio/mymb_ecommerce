
from mymb_ecommerce.mymb_b2c.settings.media import Media
from mymb_ecommerce.mymb_b2c.settings.configurations import Configurations
from mymb_ecommerce.utils.database import Database
import frappe
from frappe import _
from sqlalchemy import text
import json
from mymb_ecommerce.utils.solr import Solr

config = Configurations()
solr_instance = config.get_solr_instance()
image_uri_instance = config.get_image_uri_instance()

# Add the following imports at the beginning of your filestatu


# Update the update_categories function
@frappe.whitelist(allow_guest=True)
def get_all_data(id):
    db = config.get_mysql_connection()  