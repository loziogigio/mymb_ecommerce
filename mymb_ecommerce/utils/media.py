
import frappe
import os
from frappe import _

def get_website_domain():
    site_name = frappe.local.site
    sites_folder = frappe.get_app_path('frappe', '..', '..', 'sites')

    site_config_path = os.path.join(sites_folder, site_name, 'site_config.json')
    if os.path.exists(site_config_path):
        with open(site_config_path, 'r') as site_config_file:
            site_config = frappe._dict(frappe.parse_json(site_config_file.read()))

        if site_config.host_name:
            website_domain = f"https://{site_config.host_name}"
        else:
            website_domain = frappe.utils.get_url()
    else:
        website_domain = frappe.utils.get_url()

    return website_domain