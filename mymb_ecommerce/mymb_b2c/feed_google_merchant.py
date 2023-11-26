from mymb_ecommerce.utils.Media import Media
from mymb_ecommerce.mymb_b2c.settings.configurations import Configurations
from mymb_ecommerce.mymb_b2c.solr_search import catalogue
from omnicommerce.controllers.pdf import create_folder_structure
from mymb_ecommerce.repository.MyBarcodRepository import MyBarcodRepository
from mymb_ecommerce.repository.MyPrecodRepository import MyPrecodRepository
from mymb_ecommerce.repository.BcartmagRepository import BcartmagRepository
import frappe
from frappe import _
from urllib.parse import urlparse, parse_qs
import xml.etree.ElementTree as ET
from lxml import etree as ET
import re
from google.oauth2 import service_account
from googleapiclient.discovery import build
import json

def sanitize_text(text):
    """Remove control characters and NULL bytes from text."""
    if text:
        # Remove control characters and NULL bytes
        text = re.sub(r'[\x00-\x1F\x7F]', '', text)
        # Ensure the text is Unicode
        return text.encode('utf-8').decode('utf-8')
    return text

def add_cdata_lxml(text, parent_element):
    """
    Adds a sanitized CDATA section to a given parent XML element.

    Args:
    text (str): The text to be wrapped in a CDATA section.
    parent_element (lxml.etree._Element): The parent element to which the CDATA section will be added.
    """
    sanitized_text = sanitize_text(text)
    cdata = ET.CDATA(sanitized_text)
    parent_element.text = cdata


@frappe.whitelist(allow_guest=True, methods=['POST'])
def init_feed_generation( folder , file_name ,feed_type , args=None , limit = 100):
    config = Configurations()
    b2c_name = config.b2c_title if config.b2c_title else 'Shop'
    b2c_url = config.b2c_url if config.b2c_url else 'https://www.omnicommerce.cloud'

    # Create new Feed document
    new_feed = frappe.get_doc({
        "doctype": "Feed",
        "feed_type": feed_type ,  # Set appropriately
    })
    new_feed.insert(ignore_permissions=True)

    extra_args= {
        "per_page":limit #is going to be the max number of item to procces
    }
    unified_args = {**extra_args, **args}
    # Get the products list from the catalogue function
    result = catalogue(unified_args)  # Ensure this returns a list of product dictionaries
    products = result.get("products" , {})

    ids = []
    for product in products:
        ids.append(product['id'])


    bcartmag_repo = BcartmagRepository()
    filter_oarti = {
        "oarti":ids
    }
    bcartmags = bcartmag_repo.get_all_records_by_channell_product(filters=filter_oarti , to_dict=True)


    # Initialize the root of the XML
    rss = ET.Element("rss", version="1.0", xmlns_g="http://base.google.com/ns/1.0")
    channel = ET.SubElement(rss, "channel")

    # Add metadata about the feed
    ET.SubElement(channel, "title").text = b2c_name
    ET.SubElement(channel, "link").text = b2c_url


    # Iterate over products and add them to the XML
    for i, product in enumerate(products):
        item = ET.SubElement(channel, "item")
        
        # Add product details with CDATA
        g_id = ET.SubElement(item, "id")
        g_id.text = ET.CDATA(product['sku'])

        g_title = ET.SubElement(item, "title")
        g_title.text = ET.CDATA(product['name'])

        g_description = ET.SubElement(item, "description")
        description = product.get("short_description") if product.get("short_description") else product.get("description", "")
        g_description.text = ET.CDATA(description)

        g_link = ET.SubElement(item, "link")
        g_link.text = f"{b2c_url}/{product['slug']}"

        # Assuming product_type is available in your product data
        g_product_type = ET.SubElement(item, "product_type")
        # Initialize an empty string to keep track of the concatenated group values
        concatenated_groups = ''

        # The sorted() function ensures that the fields are processed in order: group_1, group_2, group_3, etc.
        for field in sorted(product):
            if field.startswith("group_"):
                # Replace spaces with hyphens in the current group value
                group_value_with_hyphens = product[field]
                
                # If concatenated_groups is not empty, add a comma before appending the new group value
                if concatenated_groups:
                    concatenated_groups += " > "
                    
                # Append the current group value to the concatenated string
                concatenated_groups += group_value_with_hyphens

        product_type = concatenated_groups if concatenated_groups!="" else "DEFAULT > GENERICA" 

        g_product_type.text = ET.CDATA(product_type) # Update this as needed 

       

         # Add images
        images = product.get('main_pictures', [])
        for img_index, image in enumerate(images, start=1):
            # Add main or additional_image
            image_key = "image_link" if img_index == 1 else "additional_image_link"
            image_element = ET.SubElement(item, image_key)
            
            # Assuming 'url' is the key in the 'image' dictionary that contains the image URL
            image_url = image.get('url', '')
            if image_url:
                image_element.text = ET.CDATA(image_url)


        # Other details like condition, availability, price, shipping, and brand
        g_condition = ET.SubElement(item, "condition")
        g_condition.text = "new"  # Update this as needed

        g_availability = ET.SubElement(item, "availability")
        stock = product.get("stock", "0")
        stock_text = "in_stock" if stock > 0 else "out_of_stock"
        g_availability.text = stock_text  # Update this as needed

        if product.get("is_sale"):
            g_price = ET.SubElement(item, "price")
            # Convert price to string and assign directly
            g_price.text = f"{product.get('price', '0')} EUR" 

            g_sale_price = ET.SubElement(item, "sale_price")
            # Convert sale price to string and assign directly
            g_sale_price.text = f"{product.get('sale_price', '0')} EUR"
            final_price = product.get("sale_price")
        else:
            g_price = ET.SubElement(item, "price")
            # Convert price to string and assign directly
            g_price.text = f"{product.get('price', '0')} EUR" 
            final_price = product.get("price")


        # Shipping details
        g_shipping = ET.SubElement(item, "shipping")
        g_service = ET.SubElement(g_shipping, "service")
        g_service.text = "Standard"  # Update this as needed
        g_shipping_price = ET.SubElement(g_shipping, "price")
        g_shipping_price.text = "0 EUR" if final_price > 300 else "9.90 EUR"  # Update this as needed
        g_shipping_country = ET.SubElement(g_shipping, "country")
        g_shipping_country.text = "IT"  # Update this as needed

        g_brand = ET.SubElement(item, "brand")
        brand = bcartmags[i]["brand"] if bcartmags[i]["brand"] else ""
        g_brand.text = ET.CDATA(brand)

        g_gtin = ET.SubElement(item, "gtin")
        barcode = bcartmags[i]["barcode"] if bcartmags[i]["barcode"] else ""
        g_gtin.text = ET.CDATA(barcode)

    # Write the XML to a file
    tree = ET.ElementTree(rss)

    feed_attachment =  save_and_attach( content=tree , folder=folder,file_name=file_name , attached_to_name= new_feed.name , to_doctype=new_feed.doctype)

    file_url =  feed_attachment.file_url if feed_attachment.file_url else ""

    # Update the Feed document with the file URL
    new_feed.db_set("feed_url", file_url)

    frappe.db.commit()

    return {
        "data":feed_attachment
    }




def save_and_attach(content, folder, file_name , to_doctype , attached_to_name ):
    """
    Save content to disk and create a File document.

    File document is linked to another document.
    """

    # Check if folder exists, if not create it
    create_folder_structure(folder)

    # Convert XML content to string
    xml_string = ET.tostring(content.getroot(), encoding='utf-8', method='xml')

    file = frappe.new_doc("File")
    file.file_name = file_name
    file.content = xml_string
    file.folder = folder
    file.is_private = 0
    file.attached_to_doctype = to_doctype
    file.attached_to_name = attached_to_name
    # Set the flag to ignore permissions
    file.flags.ignore_permissions = True
    file.save()
    frappe.db.commit() 

    return file





@frappe.whitelist(allow_guest=True, methods=['POST'])
def upload_to_google_merchant_create_product(args , merchant_id, credentials_json , per_page, limit=100 , batch_size=None , starting_page=1):

    args = json.loads(args) if isinstance(args, str) else args
    credentials_json = json.loads(credentials_json) if isinstance(credentials_json, str) else credentials_json


    credentials = service_account.Credentials.from_service_account_info(credentials_json)
    service = build('content', 'v2.1', credentials=credentials)

    responses = []


    config = Configurations()
    b2c_name = config.b2c_title if config.b2c_title else 'Shop'
    b2c_url = config.b2c_url if config.b2c_url else 'https://www.omnicommerce.cloud'

    # Pagination setup
    page = starting_page
    total_count = 0
    processed_count = 0

    while True:
        extra_args = {"per_page": per_page, "page": page}
        unified_args = {**extra_args, **(args or {})}
        result = catalogue(unified_args)

        if page ==starting_page:
                total_count = result.get("totalCount", 0)

        products = result.get("products", [])
        if not products:
            break

        ids = [product['id'] for product in products]
        bcartmag_repo = BcartmagRepository()
        filter_oarti = {"oarti": ids}
        bcartmags = bcartmag_repo.get_all_records_by_channell_product(filters=filter_oarti, to_dict=True)

        # Create a mapping of product ID to bcartmag
        bcartmag_map = {bcartmag['oarti']: bcartmag for bcartmag in bcartmags}

        batch_requests = []
        for i, product in enumerate(products):
            
            
            google_product = map_goog_item(product, bcartmag_map, b2c_url)
            batch_requests.append({
                'batchId': i,
                'merchantId': merchant_id,
                'method': 'insert',
                'product': google_product
            })
            processed_count += 1

            if len(batch_requests) == batch_size or i == len(products) - 1:
                try:
                    # Send batch request
                    batch_response = service.products().custombatch(body={'entries': batch_requests}).execute()
                    responses.extend(batch_response.get('entries', []))
                    print(processed_count)
                except Exception as e:
                    print(f"Error during batch request: {e}")
                    # Optionally, log the error or handle it as needed
                    # You can also append the error to the responses list if you want to keep track of it
                    responses.append({'error': str(e), 'batch': batch_requests})
                finally:
                    batch_requests = []  # Reset for next batch
            
            if processed_count >=limit:
                return {
                    "processed_count":processed_count
                }
            
        if total_count==processed_count:
            break
        # Increment the page number for the next iteration
        page += 1

    return {
        "processed_count":processed_count
    }


def map_goog_item(product,bcartmag_map , b2c_url):
    # The sorted() function ensures that the fields are processed in order: group_1, group_2, group_3, etc.
    concatenated_groups=""
    for field in sorted(product):
        if field.startswith("group_"):
            # Replace spaces with hyphens in the current group value
            group_value_with_hyphens = product[field]
            
            # If concatenated_groups is not empty, add a comma before appending the new group value
            if concatenated_groups:
                concatenated_groups += " > "
                
            # Append the current group value to the concatenated string
            concatenated_groups += group_value_with_hyphens

    categories = concatenated_groups if concatenated_groups!="" else "DEFAULT > GENERICA" 

    stock = product.get("stock", "0")
    stock_text = "in_stock" if stock > 0 else "out_of_stock"

    if product.get("is_sale"):
        sale_price = product.get('sale_price', 0)
        # Convert sale price to string and assign directly
        final_price = product.get("price")
    else:
        final_price = product.get("price")


    # Shipping details

    g_shipping_price = 0 if final_price > 300 else 9.90  # Update this as needed

    brand = ""
    barcode =""
    bcartmag = bcartmag_map.get(product['id'])
    if bcartmag:
        brand = bcartmag.get("brand", "")
        barcode = bcartmag.get("barcode", "")

        # Add images
    images = product.get('main_pictures', [])
    image_link =""
    additional_image_link = []
    for img_index, image in enumerate(images, start=1):
        # Add main or additional_image
        if img_index == 1:
            image_link = image.get('url', '')
        else: 
            additional_image_link.append( image.get('url', ''))

    google_product = {
        'offerId': product['sku'],
        'title': product['name'],
        'description': product.get("short_description") if product.get("short_description") else product.get("description", ""),
        'link': f"{b2c_url}/{product['slug']}",
        'imageLink': image_link,
        'additionalImageLinks':additional_image_link,
        'contentLanguage': 'it',
        'targetCountry': 'IT',
        'channel': 'online',
        'availability': stock_text,
        'condition': 'new',
        'googleProductCategory': categories,
        'brand': brand,
        'gtin': barcode,
        'price': {
            'value':final_price ,
            'currency': 'EUR'
        },
        'shipping': [{
            'country': 'IT',
            'service': 'Standard shipping',
            'price': {
                'value': g_shipping_price,
                'currency': 'EUR'
            }
        }]
    }
    ##Adding the sale price
    if product.get("is_sale"):
        google_product['salePrice']={
            'value':sale_price ,
            'currency': 'EUR'
        }
    
    return google_product