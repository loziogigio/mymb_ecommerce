import frappe
from frappe import _
from mymb_ecommerce.mymb_b2c.solr_action import update_solr_item_features
@frappe.whitelist()
def add_feature(doc):
    doc_dict = frappe.parse_json(doc)

   # Check if the item feature value is valid
    if not is_valid_item_feature(doc_dict['item_feature']):
        return {'message': 'Invalid item_feature value: ' + doc_dict['item_feature']}

    # check if the item feature already exists in the database
    item_feature_name = frappe.db.get_value('Item Feature', {'item_feature': doc_dict['item_feature']})

    family_name = doc_dict['family_name'].strip('\r\n\t')
    family_code = doc_dict['family_code'].strip('\r\n\t')

    if item_feature_name:
        item_feature = frappe.get_doc('Item Feature', item_feature_name)
        item_feature.family_code = family_code
        item_feature.family_name = family_name
        item_feature.erp_family_name = doc_dict['erp_family_name']
        item_feature.features = []
    else:
        item_feature = frappe.get_doc({
            "doctype": "Item Feature",
            "item_feature": doc_dict['item_feature'],
            "family_code": family_code,
            "family_name": family_name,
            "erp_family_name": doc_dict['erp_family_name']
        })

    # Save the item_feature to the database
    if item_feature_name:
        item_feature.save()
    else:
        item_feature.insert(ignore_permissions=True)
    frappe.db.commit()

    # loop through each feature in the request
    # if a feature with the same name exists in the document object, update its value
    # otherwise, create a new feature row and add it to the document object
    for feature in doc_dict['features']:
        feature_name = feature['feature_name'].strip('\r\n\t')
        feature_value = feature['value'].strip('\r\n\t') or None
        # feature_name_doc = feature_name
        feature_name_doc = add_feature_name(feature_name=feature_name, feature_type=feature['feature_type'], family_name =family_name, family_code = family_code, default_uom=feature.get('default_uom', None))
        add_feature_value(feature_name=feature_name_doc, feature_value= feature_value, family_name =family_name, family_code = family_code)

        existing_feature_value = frappe.db.exists('Item Feature Value', {
            'item_feature': item_feature.name,
            'feature_name': feature_name
        })

        if existing_feature_value:
            item_feature_value = frappe.get_doc('Item Feature Value', existing_feature_value)
        else:
            item_feature_value = frappe.get_doc({
                "doctype": "Item Feature Value",
                "item_feature": item_feature.name,
                "feature_name": feature_name_doc,
                "feature_label": feature_name,
                "feature_type": feature['feature_type']
            })

        item_feature_value.string_value = feature.get('string_value', None)
        item_feature_value.int_value = feature.get('int_value', None)
        item_feature_value.float_value = feature.get('float_value', None)
        item_feature_value.boolean_value = feature.get('boolean_value', None)
        item_feature_value.value = feature.get('value', None)
        

        if existing_feature_value:
            item_feature_value.save()
        else:
            item_feature_value.insert(ignore_permissions=True)
        frappe.db.commit()

        # Append the item_feature_value object to the item_feature.features list
        item_feature.append("features", item_feature_value)

 

    # Update the item features in Solr
    solr_update_result = update_solr_item_features(features=item_feature)

    if 'error' in solr_update_result:
        return {'message': 'Item Feature and child table records created/updated successfully, but failed to update Solr.', 'error': solr_update_result['error']}
    else:
        return {'message': 'Item Feature and child table records created/updated successfully, and Solr updated successfully.'}

    


@frappe.whitelist()
def add_feature_name(feature_name, feature_type, family_name, family_code, default_uom=None):
    # Check if Feature Name already exists
    feature_name_lower = feature_name.lower()
    existing_feature_name = frappe.db.exists('Feature Name', {
        'feature_name': feature_name_lower,
        'feature_type': feature_type,
        'default_uom': default_uom
    })

    if not existing_feature_name:
        # Create new Feature Name record
        feature_name_doc = frappe.get_doc({
            "doctype": "Feature Name",
            "feature_name": feature_name_lower,
            "feature_label": feature_name,
            "feature_type": feature_type,
            "default_uom": default_uom
        })
        try:
            feature_name_doc.insert(ignore_permissions=True)
        except frappe.DuplicateEntryError as e:

            # If the entry doesn't exist, handle the DuplicateEntryError as before
            if default_uom:
                new_feature_name = f"{feature_name}_{feature_type}_{default_uom}"
            else:
                new_feature_name = f"{feature_name}_{feature_type}"

            new_feature_name_lower = new_feature_name.lower()

            # If a DuplicateEntryError is raised, check if the entry already exists with the same primary key


            existing_new_feature_name = frappe.db.exists('Feature Name', {
                'feature_name': new_feature_name_lower,
                'feature_type': feature_type,
                'default_uom': default_uom
            })
            if existing_new_feature_name:
                # If the new feature name already exists, raise an error
                feature_name_doc = frappe.get_doc('Feature Name', existing_new_feature_name)
            else:
                # Rename the feature name and create a new Feature Name record
                feature_name_doc.name = new_feature_name_lower
                feature_name_doc.feature_name = new_feature_name_lower
                feature_name_doc.feature_label = feature_name
                feature_name_doc.feature_type = feature_type
                feature_name_doc.default_uom = default_uom
                feature_name_doc.insert(ignore_permissions=True)
    else:
        # Get the existing Feature Name record
        feature_name_doc = frappe.get_doc('Feature Name', existing_feature_name)

    #Check if Features Family List already exists
    existing_feature_family = frappe.db.exists('Feature Family', {
        'feature_name': feature_name_doc.name,
        'family_code': family_code
    })

    if not existing_feature_family:
        # Create new Feature Name Family record
        feature_family_doc = frappe.get_doc({
            "doctype": "Feature Family",
            "feature_name": feature_name_doc.name,
            "family_name": family_name,
            "family_code": family_code,
            "default_uom": default_uom

        })
        feature_family_doc.insert(ignore_permissions=True)
        frappe.db.commit()

    # Return the Feature Name document
    return feature_name_doc.name





@frappe.whitelist()
def add_feature_value(feature_name, feature_value , family_name, family_code):
    feature_name_doc = frappe.db.get('Feature Name', feature_name)

    if feature_name_doc:
        existing_feature_value = frappe.db.exists('Feature Value', {'feature_name': feature_name_doc.name, 'value': feature_value,'family_code': family_code,})

        if not existing_feature_value:
            feature_value_doc = frappe.get_doc({
                "doctype": "Feature Value",
                "feature_name": feature_name_doc.name,
                "value": feature_value,
                "family_name": family_name,
                "family_code": family_code
            })
            feature_value_doc.insert(ignore_permissions=True)
            frappe.db.commit()
            return {'message': 'Feature Value created successfully.'}
        else:
            return {'message': 'Feature Value already exists for the given Feature Name.'}
    else:
        return {'message': 'Feature Name not found.'}

def is_valid_item_feature(item_feature):
    # Add your validation logic here. For example, if the item_feature should always start with 'IEX', you can do:
    return frappe.db.exists('Item', item_feature)

@frappe.whitelist()
def get_item_feature_by_name(item_feature_name):
    # Check if the item feature exists in the database
    item_feature_doc = frappe.get_doc("Item Feature", item_feature_name)
    if not item_feature_doc:
        return {'message': 'Item Feature not found.'}

    # Get all features and their feature values for the given Item Feature
    features = []
    for feature in item_feature_doc.features:
        feature_details = {
            "feature_label": feature.feature_label,
            "feature_type": feature.feature_type,
            "string_value": feature.string_value,
            "int_value": feature.int_value,
            "float_value": feature.float_value,
            "boolean_value": feature.boolean_value,
            "value": feature.value
        }
        features.append(feature_details)

    # Return the Item Feature and its features with values
    return {
        "item_feature": item_feature_name,
        "family_code": item_feature_doc.family_code,
        "family_name": item_feature_doc.family_name,
        "erp_family_name": item_feature_doc.erp_family_name,
        "features": features
    }


@frappe.whitelist()
def get_features_by_item_name(item_name):
    # Check if the item feature exists in the database
    return item_name


