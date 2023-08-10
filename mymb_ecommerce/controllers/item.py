import frappe
from mymb_ecommerce.repository.BcartmagRepository import BcartmagRepository
from mymb_ecommerce.repository.DataRepository import DataRepository
from mymb_ecommerce.repository.MediaRepository import MediaRepository
from mymb_ecommerce.utils.MymbAPIClient import MymbAPIClient
from mymb_ecommerce.mymb_b2c.settings.configurations import Configurations
from datetime import datetime
from frappe.utils.password import update_password
from mymb_ecommerce.controllers.solr_crud import add_document_to_solr
from bs4 import BeautifulSoup
from slugify import slugify
from datetime import datetime


config = Configurations()



@frappe.whitelist(allow_guest=True, methods=['POST'])
def get_items_from_external_db(limit=None, time_laps=None, page=1,  filters=None, fetch_property=False, fetch_media=False , fetch_price=False):
    # Initialize the BcartmagRepository
    item_repo = BcartmagRepository()

    # Fetch all the Bcartmag items from the external database
    external_items = item_repo.get_all_records(limit=limit,page=page, time_laps=time_laps, filters=filters, to_dict=True)

    if fetch_property or fetch_media or fetch_price:
        # Get all distinct entity_codes from the Bcartmag records
        entity_codes = set(record['oarti'] for record in external_items)
    
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
        all_prices = {}
        for item_code, price in zip(item_codes, prices):
            if isinstance(price, dict) and 'item_code' in price:
                price['entity_code'] = price['item_code'] 
                all_prices[price['item_code']] = price
            else:
                frappe.log_error(message=f"Price dictionary does not contain 'id' key for item code {item_code}: {price}", title=f"Item ID:{item_code}From Ext DB/Missing Key Error")
                continue
        # For each record, match associated Price from the fetched prices
        for record in external_items:
            if record['oarti'] in all_prices:
                record['prices'] = all_prices[record['oarti']]
            else:
                frappe.log_error(message=f"Item {record['oarti']} has no price", title="Item From Ext DB/No Price Error")
        

    return {
        "data": external_items,
        "count": len(external_items)
    }

@frappe.whitelist(allow_guest=True, methods=['POST'])
def import_items_in_solr(limit=None, page=None, time_laps=None, filters=None, fetch_property=False, fetch_media=False , fetch_price=False):
    items = get_items_from_external_db(limit=limit, page=page,time_laps=time_laps, filters=filters, fetch_property=fetch_property, fetch_media=fetch_media, fetch_price=fetch_price)

    success_items = []
    failure_items = []
    skipped_items = []

    for item in items["data"]:
        solr_document = transform_to_solr_document(item)

        # Skip if solr_document is None, or if item['properties'] or item['medias'] is empty or missing
        if solr_document is None or not item.get('properties') or not item.get('medias'):
            sku = item.get('carti', "No code available")
            skipped_items.append(sku)
            frappe.log_error(f"Warning: Skipped Item in solr  SKU: {sku} , D: {solr_document['id']}  to Solr", f"Skipped document with SKU: {sku} due to missing slug or prices or properties or medias. {solr_document}")
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


def transform_to_solr_document(item):
    prices = item.get('prices', None)
    properties = item.get('properties', [])
    id =  item.get('oarti', None)
    sku = item.get('carti', None)
    
    properties_map = {property['property_id']: property['value'] for property in properties}
    name = properties_map.get('title_frontend', item.get('tarti', None))
    name = BeautifulSoup(name, 'html.parser').get_text() if name else None

    slug = "det/"+slugify(name + "-" + sku) if name and sku else None
    # If slug is None, return None to skip this item
    if slug is None or prices is None or id is None or sku is None:
        return None
    
    short_description = properties_map.get('short_description', item.get('tarti_swebx', None))
    short_description = BeautifulSoup(short_description, 'html.parser').get_text() if short_description else None
    description = properties_map.get('long_description', None)
    description = BeautifulSoup(description, 'html.parser').get_text() if description else None

    brand = properties_map.get('brand', None)
    images = [item['path'] + '/' + item['filename'] for item in item.get('medias', [])]

    

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
    
    solr_document = {
        "id": id,
        "sku": sku,
        "availability": availability,
        "name": name,
        "name_nostem": name,
        "short_description": short_description,
        "short_description_nostem": short_description,
        "description": description,
        "description_nostem": description,
        "sku_father": item.get('sku_father', None),
        "num_images": len(images),
        "images": images,
        "id_brand": item.get('id_brand', []),
        "id_father": item.get('id_father', None),
        "keywords": item.get('keywords', None),
        "model": item.get('model', None),
        "model_nostem": item.get('model_nostem', None),
        "discount_value":discount_value,
        "discount_percent":discount_percent,
        "slug": slug,
        "synonymous": item.get('synonymous', None),
        "synonymous_nostem": item.get('synonymous_nostem', None),
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
        "pricelist_code": prices.get('pricelist_code', None)
    }

    return solr_document
