import frappe
from mymb_ecommerce.repository.BcartmagRepository import BcartmagRepository
from mymb_ecommerce.repository.DataRepository import DataRepository
from mymb_ecommerce.repository.MediaRepository import MediaRepository
from mymb_ecommerce.repository.FeatureRepository import FeatureRepository
from mymb_ecommerce.utils.MymbAPIClient import MymbAPIClient
from mymb_ecommerce.mymb_b2c.settings.configurations import Configurations
from datetime import datetime
from frappe.utils.password import update_password
from mymb_ecommerce.controllers.solr_crud import add_document_to_solr
from bs4 import BeautifulSoup
from slugify import slugify
from datetime import datetime
from sqlalchemy import text
import json
import re


@frappe.whitelist(allow_guest=True, methods=['POST'])
def get_count_items_from_external_db( time_laps=None, filters=None , channel_id=None):
    item_repo = BcartmagRepository()
    return item_repo.get_record_count_by_channell_product( time_laps=time_laps, filters=filters ,  channel_id=channel_id)


@frappe.whitelist(allow_guest=True, methods=['POST'])
def get_items_from_external_db(limit=None, time_laps=None, page=1,  filters=None, fetch_property=False, fetch_media=False , fetch_price=False , fetch_categories=True , channel_id=None , fetch_features=True , feature_channel_id='DEFAULT'):
    # Initialize the BcartmagRepository
    item_repo = BcartmagRepository()
    config = Configurations()

    # Fetch all the Bcartmag items from the external database
    external_items = item_repo.get_all_records(limit=limit,page=page, time_laps=time_laps, filters=filters, to_dict=True , channel_id=channel_id)

    


    if fetch_property or fetch_media or fetch_price:
        # Get all distinct entity_codes from the Bcartmag records
        entity_codes = set(record['oarti'] for record in external_items)
    
    if len(entity_codes) == 0:
        return {
            "data": 0,
            "message":"No records"
        }




    if fetch_categories:
        # Fetch categories records for all entity_codes
        category_records = get_categories(item_codes=entity_codes )
        # Create a dictionary where the keys are entity_codes and the values are lists of Data objects
        all_categories = {}
        for category in category_records['results']:
            if category.get('product_code') not in all_categories:
                all_categories[category.get('product_code')] = []
            all_categories[category.get('product_code')] = category

        # For each record, match associated Category from the fetched Category records
        for record in external_items:
            record['categories'] = all_categories.get(record['oarti'], {})
            
    

    if fetch_property:
        data_repo = DataRepository()

        # Fetch Data records for all entity_codes
        data_records = data_repo.get_data_by_entity_codes(entity_codes)

        # Create a dictionary where the keys are entity_codes and the values are lists of Data objects
        all_properties = {}
        for data in data_records:
            if data.entity_code not in all_properties:
                all_properties[data.entity_code] = []
            all_properties[data.entity_code].append(data)

        # For each record, match associated Data from the fetched Data records
        for record in external_items:
            record['properties'] = all_properties.get(record['oarti'], [])
            record['properties'] = [property.to_dict() for property in record['properties']]
            
    if fetch_features:
        feature_repo = FeatureRepository()

        # Fetch Data records for all entity_codes
        feature_records = feature_repo.get_features_by_entity_codes(entity_codes , channel_id=feature_channel_id)

        # For each record, match associated Feature from the fetched Feature records
        for record in external_items:
            record['features'] = feature_records.get(record['oarti'], [])


    if fetch_media:
        media_repo = MediaRepository()

        # Fetch Media records for all entity_codes
        media_records = media_repo.get_data_by_entity_codes(entity_codes)

        # Create a dictionary where the keys are entity_codes and the values are lists of Media objects
        all_medias = {}
        for media in media_records:
            if media.entity_code not in all_medias:
                all_medias[media.entity_code] = []
            all_medias[media.entity_code].append(media)

        # For each record, match associated Media from the fetched Media records
        for record in external_items:
            record['medias'] = all_medias.get(record['oarti'], [])
            record['medias'] = [media.to_dict() for media in record['medias']]

    if fetch_price:
        default_customer_code = config.get_mymb_b2c_customer_code()
        default_customer_address_code = config.get_mymb_b2c_customer_address_code()
        client = MymbAPIClient()
        item_codes = list(entity_codes)
        quantity_list = [1 for _ in range(len(item_codes))]  # Assuming quantity 1 for all items
        prices = client.get_multiple_prices(default_customer_code, default_customer_address_code, item_codes, quantity_list)

        # Create a dictionary where the keys are item_codes and the values are prices
        try:
            all_prices = {}
            for item_code, price in zip(item_codes, prices):
                if isinstance(price, dict) and 'item_code' in price:
                    price['entity_code'] = price['item_code'] 
                    all_prices[price['item_code']] = price
                else:
                    frappe.log_error(message=f"Price dictionary does not contain 'id' key for item code {item_code}: {price}", title=f"Item ID:{item_code} From Ext DB/Missing Key Error")
                    continue

            # For each record, match associated Price from the fetched prices
            for record in external_items:
                if record['oarti'] in all_prices:
                    record['prices'] = all_prices[record['oarti']]
                else:
                    frappe.log_error(message=f"Item {record['oarti']} has no price", title="Item From Ext DB/No Price Error")

        except TypeError as e:
            message= f" item codes:{item_codes} item prices:{prices} {str(e)} "
            frappe.log_error(message=message, title="TypeError in get_items_from_external_db")

        

    return {
        "data": external_items,
        "count": len(external_items)
    }

@frappe.whitelist(allow_guest=True, methods=['POST'])
def import_items_in_solr(limit=None, page=None, time_laps=None, filters=None, fetch_property=False, fetch_media=False , fetch_price=False , fetch_categories=True , channel_id=None , feature_channel_id=None):
    items = get_items_from_external_db(limit=limit, page=page, time_laps=time_laps, filters=filters, fetch_property=fetch_property, fetch_media=fetch_media, fetch_price=fetch_price, fetch_categories=fetch_categories, channel_id=channel_id, feature_channel_id=feature_channel_id)

    success_items = []
    failure_items = []
    skipped_items = []
    log_lines = []

    if items["data"] == 0:
        return items

    for item in items["data"]:
        solr_document = transform_to_solr_document(item)
        sku = item.get('carti', "No code available")

        if solr_document is None or not item.get('medias'):
            skipped_items.append(sku)
            msg = f"⏭️ Skipped SKU: {sku} — Missing slug, prices, properties, or medias."
            log_lines.append(msg)
            continue

        result = add_document_to_solr(solr_document)
        if result['status'] == 'success':
            success_items.append(solr_document['sku'])
            log_lines.append(f"✅ Imported SKU: {solr_document['sku']}")
        else:
            failure_items.append(solr_document['sku'])
            log_lines.append(f"❌ Failed SKU: {solr_document['sku']} — Reason: {result.get('reason', 'Unknown')}")

    # Compose final log message
    log_summary = f"""
📦 Solr Import Report
▶️ Page: {page}, Limit: {limit}

✅ Success: {len(success_items)}
❌ Failure: {len(failure_items)}
⏭️ Skipped: {len(skipped_items)}

Details:
""" + "\n".join(log_lines)

    # Log it
    frappe.logger().info(log_summary)
    # Or use frappe.log_error("Solr Import Report", log_summary)

    return {
        "data": {
            "success_items": success_items,
            "failure_items": failure_items,
            "skipped_items": skipped_items,
            "summary": {
                "success": len(success_items),
                "failure": len(failure_items),
                "skipped": len(skipped_items)
            }
        }
    }




@frappe.whitelist(allow_guest=True, methods=['POST'])
def import_batch_items_in_solr(limit=None, page=None, time_laps=None, filters=None, fetch_property=False, fetch_media=False , fetch_price=False , fetch_categories=True , channel_id=None):
    items = get_items_from_external_db(limit=limit, page=page,time_laps=time_laps, filters=filters, fetch_property=fetch_property, fetch_media=fetch_media, fetch_price=fetch_price ,fetch_categories=fetch_categories , channel_id=channel_id)

    success_items = []
    failure_items = []
    skipped_items = []

    if(items["data"]== 0):
            return items
    counter=0
    for item in items["data"]:
        
        solr_document = transform_to_solr_document(item)
        print(counter)
        counter=counter+1

        if solr_document is None or not item.get('properties') or not item.get('medias'):
            sku = item.get('carti', "No code available")
            skipped_items.append(sku)
            # Log the error without trying to access 'id' in solr_document if it's None
            log_message = f"Skipped document with SKU: {sku} due to missing slug or prices or properties or medias."
            if solr_document:
                log_message += f" Document ID: {solr_document.get('id', 'No ID available')}."
            else:
                log_message += " solr_document is None."
            frappe.log_error(f"Warning: Skipped Item in solr  SKU: {sku}", log_message)
            continue

        result = add_document_to_solr(solr_document)
        if result['status'] == 'success':
            success_items.append(solr_document['sku'])
        else:
            failure_items.append(solr_document['sku'])
            frappe.log_error(title=f"Error: Import Item in solr SKU: {solr_document['sku']} ID: {solr_document['id']} ", message=f"Failed to add document with SKU: {solr_document['sku']} to Solr. Reason: {result['reason']}" )

    return {
        "data": {
            "success_items": success_items,
            "failure_items": failure_items,
            "skipped_items": skipped_items,
            "summary": {
                "success": len(success_items),
                "failure": len(failure_items),
                "skipped": len(skipped_items)
            }
        }
    }


@frappe.whitelist(allow_guest=True, methods=['POST'])
def import_items_in_erpnext(limit=None, time_laps=None, filters=None, fetch_property=False, fetch_media=False , fetch_price=False):
    items = get_items_from_external_db(limit=limit, time_laps=time_laps, filters=filters, fetch_property=fetch_property, fetch_media=fetch_media, fetch_price=fetch_price)
    
    # Transform each item to a Solr document
    solr_documents = [transform_to_solr_document(item) for item in items["data"]]

    # Add each document to Solr
    response = []
    for document in solr_documents:
        response.append(add_document_to_solr(document))

    return {
        "data": response
    }  

@frappe.whitelist(allow_guest=True, methods=['POST'])
def import_items_in_website_item(limit=None, time_laps=None, filters=None, fetch_property=False, fetch_media=False , fetch_price=False):
    items = get_items_from_external_db(limit=limit, time_laps=time_laps, filters=filters, fetch_property=fetch_property, fetch_media=fetch_media, fetch_price=fetch_price)
    
    # Transform each item to a Solr document
    solr_documents = [transform_to_solr_document(item) for item in items["data"]]

    # Add each document to Solr
    response = []
    for document in solr_documents:
        response.append(add_document_to_solr(document))

    return {
        "data": response
    }  

def transform_to_solr_document(item):
    
    prices = item.get('prices', None)
    properties = item.get('properties', [])
    id =  item.get('oarti', None)
    sku = item.get('carti', None)
    
    properties_map = {property['property_id']: property['value'] for property in properties}
    name = properties_map.get('title_frontend', item.get('tarti', None))
    name = BeautifulSoup(name, 'html.parser').get_text() if name else None

    # Truncate the slug to a maximum length (e.g., 75 characters)
    max_length = 75
    name_slug=name
    if len(name_slug) > max_length:
        name_slug = name_slug[:max_length]


    slug = "det/"+slugify(name_slug + "-" + sku) if name and sku else None
    # If slug is None, return None to skip this item
    if slug is None or prices is None or id is None or sku is None:
        return None
    
    short_description = properties_map.get('short_description', item.get('tarti_swebx', None))
    short_description = BeautifulSoup(short_description, 'html.parser').get_text() if short_description else None
    description = properties_map.get('long_description', None)
    description = BeautifulSoup(description, 'html.parser').get_text() if description else None

    brand = item.get('brand', None)
    images_cdn = [item.get('cdn', '') for item in item.get('medias', [])]
    images = images_cdn if images_cdn else [item['path'] + '/' + item['filename'] for item in item.get('medias', [])]
    
    

    

    net_price = prices.get('net_price', 0)
    net_price_with_vat = prices.get('net_price_with_vat', 0)
    gross_price = prices.get('gross_price', 0)
    gross_price_with_vat = prices.get('gross_price_with_vat', 0)
    availability = prices.get('availability', 0)
    is_promo = prices.get('is_promo', False)
    is_best_promo = prices.get('is_best_promo', False)
    promo_price = prices.get('promo_price', 0)
    promo_price_with_vat = prices.get('promo_price_with_vat', 0)

    discount_value = discount_percent = None
    if is_promo and gross_price_with_vat:
        discount_value = round(gross_price_with_vat - promo_price_with_vat,2)
        discount_percent= int((1 - promo_price_with_vat/gross_price_with_vat)*100) if gross_price_with_vat else None
        
    start_promo_date_str = prices.get('start_promo_date', None)
    end_promo_date_str = prices.get('end_promo_date', None)
    # Transform date strings to Solr date format if they are not None
    start_promo_date = datetime.strptime(start_promo_date_str, "%d/%m/%y").strftime("%Y-%m-%dT%H:%M:%SZ") if start_promo_date_str else None
    end_promo_date = datetime.strptime(end_promo_date_str, "%d/%m/%y").strftime("%Y-%m-%dT%H:%M:%SZ") if end_promo_date_str else None


    # Create a dictionary to store the values for Solr
    try:
        created_at_str = item.get('dinse_ianag', None)
    
        if created_at_str:
            created_at = created_at_str.strftime("%Y-%m-%dT%H:%M:%SZ")
        else:
            created_at = None

    except AttributeError:
        created_at = None
    except Exception as e:
        created_at = None



    # Get the current datetime in Solr's pdate format
    updated_at = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

    solr_document = {
        "id": id,
        "sku": sku,
        "availability": availability,
        "name": name,
        "name_nostem": name.lower() if isinstance(name, str) else name,
        "short_description": short_description,
        "short_description_nostem": short_description.lower() if isinstance(short_description, str) else short_description,
        "description": description,
        "description_nostem": description.lower() if isinstance(description, str) else description,
        "sku_father": item.get('sku_father', None),
        "num_images": len(images),
        "images": images,
        "brand":brand,
        "id_brand": item.get('id_brand', []),
        "id_father": item.get('id_father', None),
        "keywords": item.get('keywords', None),
        "model": item.get('model', None),
        "model_nostem": (item.get('model_nostem', None) or "").lower(),
        "discount_value":discount_value,
        "discount_percent":discount_percent,
        "gtin":item.get('barcode', None),
        "slug": slug,
        "synonymous": item.get('synonymous', None),
        "synonymous_nostem": (item.get('synonymous_nostem', None) or "").lower(),
        "gross_price": gross_price,
        "gross_price_with_vat": gross_price_with_vat,
        "net_price": net_price,
        "net_price_with_vat":net_price_with_vat ,
        "promo_code": prices.get('promo_code', None),
        "promo_price": promo_price,
        "promo_price_with_vat": promo_price_with_vat,
        "is_promo": is_promo,
        "is_best_promo": is_best_promo,
        "promo_title": prices.get('promo_title', None),
        "start_promo_date": start_promo_date,
        "end_promo_date": end_promo_date,
        "discount": prices.get('discount', [None]*6),
        "discount_extra": prices.get('discount_extra', [None]*3),
        "pricelist_type": prices.get('pricelist_type', None),
        "created_at": created_at,
        "updated_at": updated_at,
        
    }

    ##add not mandatory field
    categories = item.get('categories', None)
    if  categories:
        hierarchy = json.loads(categories.get('hierarchy'))
        # Loop through the hierarchy and add the values to the Solr document
        solr_document['family_code'] = categories['family_code']
        solr_document['family_name'] = categories['family_name']
        for h in hierarchy:
                clean_label = h['label'].strip().replace("\t", "").replace("\n", "").replace(",", " ")
                clean_label = re.sub(' +', ' ', clean_label)
                solr_document[f"group_{h['depth']}"] = clean_label  # Use the "set" modifier for partial updates

    ##add not mandatory field
    features = item.get('features', None)
    if  features:
        solr_document.update(features)

    return solr_document


@frappe.whitelist(allow_guest=True)
def get_categories(last_operation=None, count=False, args=None, item_codes=None, submenu_id=None):
    config = Configurations()
    db = config.get_mysql_connection(is_data_property=True)

    item_codes_str = None
    if item_codes is not None:
        # Convert the list to a string
        item_codes_str = ', '.join(str(code) for code in item_codes)

    submenu_id_str = None
    if submenu_id is not None:
        # Convert the list to a string
        submenu_id_str = ', '.join(str(id) for id in submenu_id)

    # Non-recursive hierarchy representation
    query_str = f"""
    SELECT 
        c1.submenu_id AS level1_id, c1.label AS level1_label,
        c2.submenu_id AS level2_id, c2.label AS level2_label,
        c3.submenu_id AS level3_id, c3.label AS level3_label,
        c4.submenu_id AS level4_id, c4.label AS level4_label,
        c5.submenu_id AS level5_id, c5.label AS level5_label,
        c6.submenu_id AS level6_id, c6.label AS level6_label,
        sp.product_code,
        sp.product_ref,
        sp.lastoperation,
        CONCAT('[', 
            JSON_OBJECT('label', c1.label, 'depth', 1), ',',
            JSON_OBJECT('label', c2.label, 'depth', 2), ',',
            JSON_OBJECT('label', c3.label, 'depth', 3), ',',
            JSON_OBJECT('label', c4.label, 'depth', 4), ',',
            JSON_OBJECT('label', c5.label, 'depth', 5), ',',
            JSON_OBJECT('label', c6.label, 'depth', 6),
        ']') AS hierarchy
    FROM channel_submenu c1
    LEFT JOIN channel_submenu c2 ON c1.submenu_id = c2.submenu_id_ref
    LEFT JOIN channel_submenu c3 ON c2.submenu_id = c3.submenu_id_ref
    LEFT JOIN channel_submenu c4 ON c3.submenu_id = c4.submenu_id_ref
    LEFT JOIN channel_submenu c5 ON c4.submenu_id = c5.submenu_id_ref
    LEFT JOIN channel_submenu c6 ON c5.submenu_id = c6.submenu_id_ref
    JOIN submenu_product sp ON sp.submenu_id = 
        CASE 
            WHEN c6.submenu_id IS NOT NULL THEN c6.submenu_id
            WHEN c5.submenu_id IS NOT NULL THEN c5.submenu_id
            WHEN c4.submenu_id IS NOT NULL THEN c4.submenu_id
            WHEN c3.submenu_id IS NOT NULL THEN c3.submenu_id
            WHEN c2.submenu_id IS NOT NULL THEN c2.submenu_id
            ELSE c1.submenu_id
        END
    WHERE c1.submenu_id_ref = 0 
    """

    if item_codes_str is not None:
        query_str += f" AND (sp.product_code IN ({item_codes_str}))"

    if submenu_id_str is not None:
        query_str += f" AND (c1.submenu_id IN ({submenu_id_str}))"

    query_str += """
    ORDER BY sp.lastoperation,sp.product_code, c1.submenu_id
    """

    query = text(query_str)

    results = db.session.execute(query, {'last_operation': last_operation}).fetchall()
    db.disconnect()

    result_list = []
    for row in results:
        # Parsing the hierarchy string into a Python list
        hierarchy = json.loads(row.hierarchy)
        
        # Filtering out the items with a null label
        filtered_hierarchy = [item for item in hierarchy if item['label'] is not None]

        # Determine the family_code (deepest submenu_id)
        family_code = (
            row.level6_id if row.level6_id is not None else
            row.level5_id if row.level5_id is not None else
            row.level4_id if row.level4_id is not None else
            row.level3_id if row.level3_id is not None else
            row.level2_id if row.level2_id is not None else
            row.level1_id
        )

         # Determine the family_name (label of the deepest submenu_id)
        family_name = (
            row.level6_label if row.level6_id is not None else
            row.level5_label if row.level5_id is not None else
            row.level4_label if row.level4_id is not None else
            row.level3_label if row.level3_id is not None else
            row.level2_label if row.level2_id is not None else
            row.level1_label
        )

        
        
        result_dict = {
            'submenu_id': row.level1_id,
            'family_code' : family_code,
            'family_name' : family_name,
            'product_code': row.product_code,
            'product_ref': row.product_ref,
            'lastoperation': row.lastoperation,
            'hierarchy': json.dumps(filtered_hierarchy),  # Converting the list back to a string representation
        }
        result_list.append(result_dict)
        
    # if count:
    #     result_list.append({'total_results': total_results})
    
    # Construct the response
    response =  {
        'results': result_list
    }
    
    # if count:
    #     response['total_results'] = total_results

    return response

