import frappe
from frappe import _
from mymb_ecommerce.controllers.solr_action import update_solr_item_features

@frappe.whitelist()
def add_feature_list(docs):
    # Parse the JSON string into a list of docs
    docs_list = frappe.parse_json(docs)
    
    # Iterate through each doc in the list
    for doc in docs_list:
        # Call the add_feature function for each doc
        add_feature(doc)

@frappe.whitelist()
def add_feature(doc_dict):
    try:
        # If doc is a JSON string, parse it into a dictionary
        if isinstance(doc_dict, str):
            doc_dict = frappe.parse_json(doc_dict)

        # Validate the input dictionary
        if not isinstance(doc_dict, dict):
            return {'message': 'Invalid input: expected a dictionary or JSON string'}

        # Check if required keys are in the doc_dict
        required_keys = ['item_feature', 'family_name', 'family_code', 'erp_family_name', 'features']
        for key in required_keys:
            if key not in doc_dict:
                return {'message': f'Missing required key: {key}'}

        # Check if the item feature value is valid
        if not is_valid_item_feature(doc_dict['item_feature']):
            return {'message': 'Invalid item_feature value: ' + doc_dict['item_feature']}

        family_name = doc_dict['family_name'].strip('\r\n\t')
        family_code = doc_dict['family_code'].strip('\r\n\t')

        item_feature_name = frappe.db.get_value('Item Feature', {'item_feature': doc_dict['item_feature']})

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
        for feature in doc_dict.get('features', []):
            if 'feature_name' not in feature or 'feature_type' not in feature:
                continue
            feature_name = feature['feature_name'].strip('\r\n\t')
            feature_value = feature.get('value', '').strip('\r\n\t') or None
            feature_default_uom = feature.get('feature_uom', '').strip('\r\n\t') or None

            feature_name_doc = add_feature_name(feature_name=feature_name, feature_type=feature['feature_type'], family_name=family_name, family_code=family_code, default_uom=feature_default_uom)
            add_feature_value(feature_name=feature_name_doc, feature_value=feature_value, family_name=family_name, family_code=family_code)

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

    except Exception as e:
        # Catch any unexpected exception and return a message
        return {'message': 'An unexpected error occurred', 'error': str(e)}



@frappe.whitelist()
def add_feature_name(feature_name, feature_type, family_name, family_code, default_uom=None):
    # Convert feature_name to lowercase for consistency
    feature_name_lower = feature_name.lower()
    
    # Check if Feature Name already exists
    existing_feature_name = frappe.db.exists('Feature Name', {
        'feature_label': feature_name_lower,
        'feature_type': feature_type,
        'default_uom': default_uom
    })

    if not existing_feature_name:
        # Create new Feature Name record
        feature_name_doc = frappe.get_doc({
            "doctype": "Feature Name",
            "feature_name": feature_name_lower,
            "feature_label": feature_name_lower,
            "feature_type": feature_type,
            "default_uom": default_uom
        })
        
        try:
            # Mute messages
            frappe.flags.mute_messages = True
            # Try inserting the new feature name record
            feature_name_doc.insert(ignore_permissions=True)
        except frappe.DuplicateEntryError as e:

            # Log the error for debugging purposes
            frappe.log_error(frappe.get_traceback(), f"f name: {feature_name_lower}, type: {feature_type} , family : {family_name} {family_code} Duplicate Entry Error while inserting Feature Name")

            # Construct a new feature name if a duplicate error occurs
            if default_uom:
                new_feature_name = f"{feature_name}_{feature_type}_{default_uom}"
            else:
                new_feature_name = f"{feature_name}_{feature_type}"
            new_feature_name_lower = new_feature_name.lower()

            # Check if the new feature name already exists
            existing_new_feature_name = frappe.db.exists('Feature Name', {
                'feature_name': new_feature_name_lower,
                'feature_type': feature_type,
                'default_uom': default_uom
            })
            
            if existing_new_feature_name:
                # If the new feature name already exists, get the existing document
                feature_name_doc = frappe.get_doc('Feature Name', existing_new_feature_name)
            else:
                # Create a new Feature Name record with the renamed feature name
                feature_name_doc = frappe.get_doc({
                    "doctype": "Feature Name",
                    "feature_name": new_feature_name_lower,
                    "feature_label": feature_name_lower,
                    "feature_type": feature_type,
                    "default_uom": default_uom
                })
                feature_name_doc.insert(ignore_permissions=True)
        finally:
            # Unmute messages
            frappe.flags.mute_messages = False
    else:
        # If Feature Name already exists, get the existing document
        feature_name_doc = frappe.get_doc('Feature Name', existing_feature_name)

    # Check if Feature Family List already exists
    existing_feature_family = frappe.db.exists('Feature Family', {
        'feature_name': feature_name_doc.name,
        'family_code': family_code
    })

    if not existing_feature_family:
        # Create a new Feature Family record
        feature_family_doc = frappe.get_doc({
            "doctype": "Feature Family",
            "feature_name": feature_name_doc.name,
            "family_name": family_name,
            "family_code": family_code,
            "family_uom": default_uom
        })
        feature_family_doc.insert(ignore_permissions=True)
        frappe.db.commit()

    # Return the Feature Name document name
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
    features = {}
    
    # Get item feature values along with feature metadata
    results = frappe.db.sql("""
        SELECT 
            fn.feature_label,
            fn.feature_type,
            fn.default_uom,
            ifv.string_value,
            ifv.int_value,
            ifv.float_value,
            ifv.boolean_value,
            ff.family_uom
        FROM 
            `tabItem Feature Value` as ifv
        JOIN
            `tabFeature Name` as fn
        ON
            ifv.feature_label = fn.feature_name
        LEFT JOIN
            `tabFeature Family` as ff
        ON
            fn.feature_name = ff.feature_name
        WHERE
            ifv.item_feature = %s
    """, (item_name), as_dict=True)
    
    # Process the results
    for result in results:
        feature_label = result["feature_label"]
        default_uom = result["family_uom"] if result["family_uom"] else result["default_uom"]
        
        if result["feature_type"] == "string":
            value = result["string_value"]
            if value == "":
                continue
        elif result["feature_type"] == "int" or result["feature_type"] == "float":
            value = result["int_value"] if result["feature_type"] == "int" else result["float_value"]
            if value <= 0:
                continue
        elif result["feature_type"] == "boolean":
            value = bool(result["boolean_value"])
            if value == "":
                continue
        else:
            continue

        # Add the feature to the dictionary
        features[feature_label] = {"value": value, "default_uom": default_uom}
    
    return features



@frappe.whitelist(allow_guest=True, methods=['GET'])
def get_features_by_family_code(family_code):
    # Query the database to fetch the feature_name and default_uom for the given family_code
    results = frappe.db.sql("""
        SELECT
            ff.feature_name,fn.feature_label,fn.feature_type,
            IF(ff.family_uom IS NOT NULL AND ff.family_uom != '', ff.family_uom, fn.default_uom) AS default_uom
        FROM
            `tabFeature Family` AS ff
        LEFT JOIN
            `tabFeature Name` AS fn
        ON
            ff.feature_name = fn.feature_name
        WHERE
            ff.family_code = %s
    """, (family_code), as_dict=True)

    # Transform the result into a dictionary
    features = {result["feature_name"]: {"feature_type": result["feature_type"],"feature_label": result["feature_label"],"default_uom": result["default_uom"]} for result in results}

    return features

def map_feature_with_uom_via_family_code(features, items):
    # Type mapping dictionary
    type_map = {"f": "float", "i": "int", "s": "string", "b": "boolean"}
    
    # Loop through items and stop at the first occurrence of family_code
    family_code = None
    for item in items:
        if "family_code" in item and item["family_code"]:
            family_code = item["family_code"]
            break
    
    # If no family_code was found, return the original features
    if not family_code:
        return features
    
    feature_for_family = get_features_by_family_code(family_code)

    # Loop through features and update them
    for feature in features:
        # Check if feature name and type both exist in feature_for_family
        if feature['label_field'] in feature_for_family and type_map[feature['type']] == feature_for_family[feature['label_field']]['feature_type']:
            default_uom = feature_for_family[feature['label_field']]['default_uom']

            # Add 'uom' key to the features dictionary
            feature['uom'] = default_uom

            # Also add 'uom' to each facet result
            for facet_result in feature['facet_results']:
                facet_result['uom'] = default_uom

    return features




