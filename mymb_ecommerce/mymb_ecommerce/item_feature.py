import frappe
from mymb_ecommerce.mymb_b2c.solr_action import update_solr_item_features

@frappe.whitelist()
def add_feature(doc):
    doc_dict = frappe.parse_json(doc)

    # check if the item feature already exists in the database
    item_feature_name = frappe.db.get_value('Item Feature', {'item_feature': doc_dict['item_feature']})

    if item_feature_name:
        item_feature = frappe.get_doc('Item Feature', item_feature_name)
        item_feature.family_code = doc_dict['family_code']
        item_feature.family_name = doc_dict['family_name']
        item_feature.erp_family_name = doc_dict['erp_family_name']
        item_feature.features = []
    else:
        item_feature = frappe.get_doc({
            "doctype": "Item Feature",
            "item_feature": doc_dict['item_feature'],
            "family_code": doc_dict['family_code'],
            "family_name": doc_dict['family_name'],
            "erp_family_name": doc_dict['erp_family_name'],
            "features": []
        })

    # loop through each feature in the request
    # if a feature with the same name exists in the document object, update its value
    # otherwise, create a new feature row and add it to the document object
    for feature in doc_dict['features']:
        feature_exists = False
        for i, feature_row in enumerate(item_feature.features):
            if feature_row.feature_name == feature['feature_name']:
                feature_exists = True
                item_feature.features[i].value = feature.get('value', None)
                item_feature.features[i].string_value = feature.get('string_value', None)
                item_feature.features[i].int_value = feature.get('int_value', None)
                item_feature.features[i].float_value = feature.get('float_value', None)
                item_feature.features[i].boolean_value = feature.get('boolean_value', None)
                break

        if not feature_exists:
            item_feature.append('features', {
                'feature_name': feature['feature_name'],
                'feature_type': feature['feature_type'],
                'value': feature.get('value', None),
                'string_value': feature.get('string_value', None),
                'int_value': feature.get('int_value', None),
                'float_value': feature.get('float_value', None),
                'boolean_value': feature.get('boolean_value', None),
            })

    # save the document object to the database
    if item_feature_name:
        item_feature.save()
    else:
        item_feature.insert(ignore_permissions=True)
    frappe.db.commit()

    # Update the item features in Solr
    solr_update_result = update_solr_item_features(doc_dict['item_feature'], doc_dict['features'])

    if 'error' in solr_update_result:
        return {'message': 'Item Feature and child table records created/updated successfully, but failed to update Solr.', 'error': solr_update_result['error']}
    else:
        return {'message': 'Item Feature and child table records created/updated successfully, and Solr updated successfully.'}

    