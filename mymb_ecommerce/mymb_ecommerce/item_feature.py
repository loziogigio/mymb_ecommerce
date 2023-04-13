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
            "erp_family_name": doc_dict['erp_family_name'],
            "features": []
        })

    # loop through each feature in the request
    # if a feature with the same name exists in the document object, update its value
    # otherwise, create a new feature row and add it to the document object
    for feature in doc_dict['features']:
        feature_name = feature['feature_name'].strip('\r\n\t')
        feature_value = feature['value'].strip('\r\n\t') or None
        # feature_name_doc = feature_name
        feature_name_doc = add_feature_name(feature_name=feature_name, feature_type=feature['feature_type'], family_name =family_name, family_code = family_code, default_uom=feature.get('default_uom', None))
        add_feature_value(feature_name=feature_name_doc, feature_value= feature_value, family_name =family_name, family_code = family_code)

        feature_exists = False
        for i, feature_row in enumerate(item_feature.features):
            # Call the add_feature_name and add_feature_value functions
            

            if feature_row.feature_name == feature_name:
                feature_exists = True
                item_feature.features[i].value = feature_value 
                item_feature.features[i].string_value = feature.get('string_value', None)
                item_feature.features[i].int_value = feature.get('int_value', None)
                item_feature.features[i].float_value = feature.get('float_value', None)
                item_feature.features[i].boolean_value = feature.get('boolean_value', None)
                break

        if not feature_exists:
            item_feature.append('features', {
                'feature_name': feature_name_doc,
                'feature_label': feature_name,
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
