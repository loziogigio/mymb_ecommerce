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
def init_feed_generation(folder, file_name, feed_type, args=None, per_page=100 , max_item=None , filters=None):
    config = Configurations()
    b2c_name = config.b2c_title if config.b2c_title else 'Shop'
    b2c_url = config.b2c_url if config.b2c_url else 'https://www.omnicommerce.cloud'

    # Create new Feed document
    new_feed = frappe.get_doc({
        "doctype": "Feed",
        "feed_type": feed_type,
    })
    new_feed.insert(ignore_permissions=True)

    # Initialize the root of the XML
    rss = ET.Element("rss", version="1.0", xmlns_g="http://base.google.com/ns/1.0")
    channel = ET.SubElement(rss, "channel")
    ET.SubElement(channel, "title").text = b2c_name
    ET.SubElement(channel, "link").text = b2c_url
    products_element = ET.SubElement(channel, "Products")

    # Pagination setup
    page = 1
    total_count = 0
    processed_count = 0

    # Fetch and process data from bcartmag and catalogue in the same loop
    bcartmag_repo = BcartmagRepository()

    while True:
        # Step 1: Fetch data from bcartmag
        bcartmags = bcartmag_repo.get_all_records_by_channell_product(limit=per_page, page=page, to_dict=True , filters=filters)

        if not bcartmags:
            break  # Exit loop if no more bcartmag records


        # Step 2: Extract oarti values (SKUs) from bcartmag
        skus_list = [bcartmag['carti'] for bcartmag in bcartmags]

        # Step 3: Query the catalogue using the SKUs from bcartmag
        skus = ";".join(skus_list)  # Create SKUs filter
        extra_args = {"per_page": per_page, "skus": skus}
        unified_args = {**extra_args, **(args or {})}
        result = catalogue(unified_args)

        # Step 4: Process the products returned from catalogue

       

        products = result.get("products", [])
        if not products:
            page += 1
            continue  # Skip to the next iteration (next page of bcartmag)

        # Create a mapping of product ID to bcartmag
        bcartmag_map = {bcartmag['oarti']: bcartmag for bcartmag in bcartmags}

        # Iterate over products and add them to the XML
        for product in products:
            # Check if max_item limit is reached
            if max_item and processed_count >= max_item:
                break

            #we are not uploading payable items that are not purchasabel
            if product.get("stock", "0")==0:
                continue

            offer = ET.SubElement(products_element, "Offer")
            
            # Add product details with CDATA
            name_element = ET.SubElement(offer, "Name")
            add_cdata_lxml(product['name'], name_element)

            # Use the mapping to get the corresponding bcartmag
            bcartmag = bcartmag_map.get(product['id'])

            brand = ""  # Initialize brand with a default value
            barcode = ""  # Initialize barcode with a default value
            if bcartmag:
                brand = bcartmag.get("brand", "")
                barcode = bcartmag.get("barcode", "")

            brand = brand if brand else ""
            brand_element = ET.SubElement(offer, "Brand")
            add_cdata_lxml(brand, brand_element)

            description = product.get("short_description") if product.get("short_description") else product.get("description", "")
            description_element = ET.SubElement(offer, "Description")
            add_cdata_lxml(description[:255], description_element)

            if product.get("is_sale"):
                prior_price_element = ET.SubElement(offer, "PriorPrice")
                # Convert price to string and assign directly
                prior_price_element.text = str(product.get("price", ""))

                price_element = ET.SubElement(offer, "Price")
                # Convert sale price to string and assign directly
                price_element.text = str(product.get("sale_price", ""))
                final_price = product.get("sale_price")
            else:
                price_element = ET.SubElement(offer, "Price")
                # Convert price to string and assign directly
                price_element.text = str(product.get("price", ""))
                final_price = product.get("price")

            code_element = ET.SubElement(offer, "Code")
            add_cdata_lxml(product['sku'], code_element)

            link_element = ET.SubElement(offer, "Link")
            add_cdata_lxml(f"{b2c_url}/{product['slug']}", link_element)

            shipping_cost_element = ET.SubElement(offer, "ShippingCost")
            shipping_cost_element.text = "0" if final_price > 300 else "9.90"

            stock_element = ET.SubElement(offer, "Stock")
            stock_element.text = str(int(product.get("stock", "0")))

            barcode = barcode if barcode else ""
            eancode_element = ET.SubElement(offer, "EanCode")
            add_cdata_lxml(barcode, eancode_element)

            # Add categories
            category_element = ET.SubElement(offer, "Categories")

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

            categories = concatenated_groups if concatenated_groups!="" else "DEFAULT > GENERICA" 

            category_element.text = ET.CDATA(categories)

            # Add images
            images = product.get('main_pictures', [])
            for img_index, image in enumerate(images, start=1):
                image_key = "Image" if img_index == 1 else f"Image{img_index}"
                image_element = ET.SubElement(offer, image_key)
                add_cdata_lxml(image['url'], image_element)

            processed_count += 1
        


        # Check if all items have been processed
        print(processed_count)
        if processed_count >= max_item:
            break

        page += 1

    # Write the XML to a file
    tree = ET.ElementTree(rss)
    feed_attachment = save_and_attach(content=tree, folder=folder, file_name=file_name, attached_to_name=new_feed.name, to_doctype=new_feed.doctype)
    file_url = feed_attachment.file_url if feed_attachment.file_url else ""
    new_feed.db_set("feed_url", file_url)
    frappe.db.commit()

    return {"data": feed_attachment}




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
