
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
def get_categories(last_operation=None, count=False, args=None):
    db = config.get_mysql_connection()  # Add this line to get the database connection from Configurations class

    query = text("""
    WITH RECURSIVE hierarchy AS (
        SELECT submenu_id, submenu_id_ref, label, depth, JSON_ARRAY(JSON_OBJECT('label', label, 'depth', depth)) AS path
        FROM channel_submenu
        WHERE submenu_id_ref = 0

        UNION ALL

        SELECT c.submenu_id, c.submenu_id_ref, c.label, c.depth, JSON_ARRAY_APPEND(h.path, '$', JSON_OBJECT('label', c.label, 'depth', c.depth))
        FROM channel_submenu c
        JOIN hierarchy h ON c.submenu_id_ref = h.submenu_id
    )
    SELECT
        h.submenu_id,
        sp.product_code,
        sp.product_ref,
        sp.lastoperation,
        ANY_VALUE(h.path) AS hierarchy
    FROM hierarchy h
    JOIN submenu_product sp ON h.submenu_id = sp.submenu_id
    WHERE (:last_operation IS NULL OR sp.lastoperation > :last_operation)
    GROUP BY h.submenu_id, sp.product_code, sp.lastoperation
    ORDER BY sp.product_code, h.submenu_id
    """)
    if count:
        count_query = text(f"SELECT COUNT(*) FROM ({query}) as subquery")
        total_results = db.session.execute(count_query, {'last_operation': last_operation}).fetchone()[0]
    results = db.session.execute(query, {'last_operation': last_operation}).fetchall()
    db.disconnect()

    result_list = []
    for row in results:
        result_dict = {
            'submenu_id': row.submenu_id,
            'product_code': row.product_code,
            'product_ref': row.product_ref,
            'lastoperation': row.lastoperation,
            'hierarchy': row.hierarchy,
        }
        result_list.append(result_dict)
    if count:
        result_list.append({'total_results': total_results})
    # Construct the response
    response =  {
        'results': result_list
    }
    if count:
        response['total_results'] = total_results

    return response

@frappe.whitelist(allow_guest=True)
def update_all_solr_category():
    # Get the categories
    solr = solr_instance.solr
    categories = get_categories()
    # Create a list to store the categories to be updated in Solr
    # Loop through each category
    failed_updates = 0
    for category in categories['results']:
        # Get the hierarchy of the category
        hierarchy = json.loads(category['hierarchy'])

        # Create a dictionary to store the values for Solr
        solr_doc = {
            "id": category['product_code'],
            "_version_": 0  # This forces a partial update
        }

        # Loop through the hierarchy and add the values to the Solr document
        for h in hierarchy:
            clean_label = h['label'].strip().replace("\t", "").replace("\n", "").replace(",", " ")
            solr_doc[f"group_{h['depth']}"] = {"set": clean_label}  # Use the "set" modifier for partial updates
        
        try:
            # Update the category in Solr using the add method with the update handler
            solr.add([solr_doc], handler='update')
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
    solr = solr_instance.solr

    family_code=features.family_code
    family_name=features.family_name
    item_code=features.item_feature
    feature_array = features.features
    # Search for the item by item_code in Solr
    try:
        search_results = solr.search(f'carti:"{item_code}"')
        if search_results.hits == 0:
            raise Exception(f'Item with item_code {item_code} not found in Solr')
        item_id = search_results.docs[0]['id']
    except Exception as e:
        error_msg = f"Failed to find item {item_code} in Solr. Error: {e}"
        frappe.log_error(error_msg)
        return {'error': error_msg}

    solr_doc = {
        "id": item_id,
        "_version_": 0  # This forces a partial update
    }

    for feature in feature_array:
        cleaned_feature_name = Solr.clean_feature_name(feature.feature_name)
        feature_suffix = Solr.get_feature_suffix(feature.feature_type)
        solr_doc['family_code'] = family_code
        solr_doc['family_name'] = family_name.lower()
        if feature_suffix:
            solr_doc[f"{cleaned_feature_name}{feature_suffix}"] = {"set": feature.get('value', None)}

    try:
        # Update the item features in Solr using the add method with the update handler
        solr.add([solr_doc], handler='update')
        solr.commit()
        return {'message': 'Item features updated successfully in Solr.'}
    except Exception as e:
        error_msg = f"Failed to update item features for item {item_code} in Solr. Error: {e}"
        frappe.log_error(error_msg)
        return {'error': error_msg}
