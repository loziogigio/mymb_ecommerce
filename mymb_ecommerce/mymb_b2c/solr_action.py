
from mymb_ecommerce.utils.Media import Media
from mymb_ecommerce.mymb_b2c.settings.configurations import Configurations
from mymb_ecommerce.utils.Database import Database
import frappe
from frappe import _
import json
from mymb_ecommerce.utils.Solr import Solr
from mymb_ecommerce.controllers.solr_crud import add_document_to_solr, update_document_in_solr
from mymb_ecommerce.mymb_b2c.item import get_categories
from slugify import slugify
import re

# Add the following imports at the beginning of your filestatu






@frappe.whitelist(allow_guest=True)
def update_all_solr_category(last_operation=None, count=False, args=None , item_codes=None , submenu_id=None):
    # Get the categories


    config = Configurations()
    solr_instance = config.get_solr_instance()

    solr = solr_instance.solr
    categories = get_categories(last_operation, count, args,item_codes , submenu_id)
    # Create a list to store the categories to be updated in Solr
    # Loop through each category
    failed_updates = 0
    for category in categories['results']:
        # Get the hierarchy of the category
        try:
            hierarchy = json.loads(category['hierarchy'])
        except KeyError:
            frappe.log_error(f"'hierarchy' key not found in the  category: {category}")
            continue

        # Create a dictionary to store the values for Solr
        solr_doc = {
            "id": category['product_code']
        }

        # Loop through the hierarchy and add the values to the Solr document
        for h in hierarchy:
            clean_label = h['label'].strip().replace("\t", "").replace("\n", "").replace(",", " ")
            clean_label = re.sub(' +', ' ', clean_label)
            solr_doc[f"group_{h['depth']}"] = clean_label  # Use the "set" modifier for partial updates
        
        try:
            # Update the category in Solr using the add method with the update handler
            update_document_in_solr(solr_doc)
        except Exception as e:
            error_msg = f"Failed to update category {category['product_code']} in Solr. Error: {e}"
            if len(error_msg) > 140:
                error_msg = error_msg[:130] + "..."
            failed_updates += 1
            frappe.log_error(error_msg)
            continue

    solr.commit()

    # Save the result in log
    frappe.log_error(f"Categories updated successfully in Solr. Total updated categories: {len(categories['results']) - failed_updates}. Total failed updates: {failed_updates}")


@frappe.whitelist(allow_guest=True)
def update_solr_item_features( features):
    config = Configurations()
    solr_instance = config.get_solr_instance()



    solr = solr_instance.solr

    family_code=features.family_code
    family_name=features.family_name
    item_code=features.item_feature
    feature_array = features.get('features', [])
    # Search for the item by item_code in Solr
    try:
        search_results = solr.search(f'sku:"{item_code}"')
        if search_results.hits == 0:
            raise Exception(f'Item with item_code {item_code} not found in Solr')
        item_id = search_results.docs[0]['id']
    except Exception as e:
        error_msg = f"Failed to find item {item_code} in Solr. Error: {e}"
        frappe.log_error(error_msg)
        return {'error': error_msg}

    solr_doc = {
        "id": item_id,
    }

    for feature in feature_array:
        cleaned_feature_name = Solr.clean_feature_name(feature.feature_name)
        feature_suffix = Solr.get_feature_suffix(feature.feature_type)
        solr_doc['family_code'] = family_code
        solr_doc['family_name'] = family_name.lower()
        if feature_suffix:
            feature_value = feature.get('value', None)
            if feature_value:
                solr_doc[f"{cleaned_feature_name}{feature_suffix}"] = feature_value

    try:
        # Update the item features in Solr using the add method with the update handler
        update_document_in_solr(solr_doc)
        return {'message': f"Item features for item {item_code} updated successfully in Solr."}
    except Exception as e:
        error_msg = f"Failed to update item features for item {item_code} in Solr. Error: {e}"
        frappe.log_error(error_msg)
        return {'error': error_msg}
