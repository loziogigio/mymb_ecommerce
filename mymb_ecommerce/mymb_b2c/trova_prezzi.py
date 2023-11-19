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

# Function to add CDATA
def add_cdata(text):
    text_str = str(text)  # Convert to string to ensure compatibility with isdigit()
    if not text_str.isdigit():
        return f'<![CDATA[{text_str}]]>'
    else:
        return text_str

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

    barcode_repo = MyBarcodRepository()
    bcartmag_repo = BcartmagRepository()
    filter_oarti = {
        "oarti":ids
    }
    barcods = barcode_repo.get_all_records(filters=filter_oarti)
    bcartmags = bcartmag_repo.get_all_records(filters=filter_oarti)


    # Initialize the root of the XML
    rss = ET.Element("rss", version="1.0", xmlns_g="http://base.google.com/ns/1.0")
    channel = ET.SubElement(rss, "channel")

    # Add metadata about the feed
    ET.SubElement(channel, "title").text = b2c_name
    ET.SubElement(channel, "link").text = b2c_url

    # Products container
    products_element = ET.SubElement(channel, "Products")

    #get bar codes as in statment

    # Iterate over products and add them to the XML
    for i, product in enumerate(products):

        offer = ET.SubElement(products_element, "Offer")
        
        # Add product details
        ET.SubElement(offer, "Name").text = add_cdata(product['name'])

        brand = bcartmags[i]["tprec_darti"] if bcartmags[i]["tprec_darti"] else ""
        ET.SubElement(offer, "Brand").text = add_cdata(brand)

        description = product.get("short_description") if product.get("short_description") else product.get("description" , "")
        ET.SubElement(offer, "Description").text = add_cdata(description[:255])

        if  product.get("is_sale"):
            ET.SubElement(offer, "PriorPrice").text = add_cdata(product.get("price"))
            ET.SubElement(offer, "Price").text = add_cdata(product.get("sale_price"))
            final_price = product.get("sale_price")
        else:
            ET.SubElement(offer, "Price").text = add_cdata(product.get("price"))
            final_price = product.get("price")

        ET.SubElement(offer, "Code").text = add_cdata(product['sku'])

        ET.SubElement(offer, "Link").text = add_cdata(f"{product['slug']}")

        
        brand = product.get("brad")[0] if product.get("brad") else ""
        ET.SubElement(offer, "Brand").text = add_cdata(brand)
        
        
        
        ET.SubElement(offer, "ShippingCost").text = "0" if final_price > 300 else "9.90"
        ET.SubElement(offer, "Stock").text = add_cdata(product.get("stock"))

        barcode = barcods[i].cbarx if barcods[i].cbarx else ""
        ET.SubElement(offer, "EanCode").text = add_cdata(barcode)

       


        # Add images
        images = product.get('main_pictures', [])  # Assuming this is how images are referenced in the product dict
        for i, image in enumerate(images, start=1):
            image_key = "Image" if i==1 else f"Image{i}"
            ET.SubElement(offer, image_key).text = add_cdata(image['url'])

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



#     to create xml code and write it in a file 
#     <?xml version="1.0"?>
# <rss xmlns:g="http://base.google.com/ns/1.0" version="2.0">
#     <channel>
#         <title>BricoCasa</title>
#         <link>https://brico-casa.it/</link> 
#         <Products>
#             <Offer>
#                 <Brand>Kingstone</Brand>
#                 <Description>Pen Drive Professional 16GB USB 2.0</Description>
#                 <PriorPrice>10.60</PriorPrice>
#                 <Price>8.60</Price>
#                 <Code>219</Code>
#                 <Link>https://www.NOMESITO.it/product.asp?Id=219</Link>
#                 <Stock>35</Stock>
#                 <Categories>informatica, chiavette usb/pen drives</Categories>
#                 <Image>https://www.NOMESITO.it/images/219.jpg</Image>
#                 <ShippingCost>0</ShippingCost>
#                 <PartNumber>TS2GJFV20</PartNumber>
#                 <EanCode>0075678164125</EanCode>
#                 <Weight>0.100</Weight>
#                 <Image2>https://www.NOMESITO.it/images/219bis.jpg</Image2>
#                 <Image3>https://www.NOMESITO.it/images/219tris.jpg</Image3>
#             </Offer>
#             <Offer>
#                 <Name>Pendrive 4GB Verbatim Store'n'go</Name>
#                 <Brand>Verbatim</Brand>
#                 <Description>Pen Drive Professional 4GB USB 2.0</Description>
#                 <PriorPrice>6.50</PriorPrice>
#                 <Price>3.50</Price>
#                 <Code>220</Code>
#                 <Link>https://www.NOMESITO.it/product.asp?Id=220</Link>
#                 <Stock>5</Stock>
#                 <Categories>informatica, chiavette usb/pen drives</Categories>
#                 <Image>https://www.NOMESITO.it/images/220.jpg</Image>
#                 <ShippingCost>0</ShippingCost>
#                 <PartNumber>49061</PartNumber>
#                 <EanCode>0075678164134</EanCode>
#                 <Weight>0.100</Weight>
#                 <Image2>https://www.NOMESITO.it/images/220bis.jpg</Image2>
#                 <Image3>https://www.NOMESITO.it/images/220tris.jpg</Image3>
#             </Offer>
#         </Products>
#     </channel>
# </rss>


# where is not a numerical value we have to set up CDATA example <Image3>https://www.NOMESITO.it/images/220tris.jpg</Image3>
# has to be 
# <Image3><![CDATA[https://www.NOMESITO.it/images/220tris.jpg]]></Image3>
