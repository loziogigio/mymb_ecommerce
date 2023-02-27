
import json
import pysolr

import frappe
from frappe import _

solr = None
image_uri = None


def get_solr_instance():
    """Get the Solr instance from the B2C Settings DocType"""

    global solr
    doc = frappe.get_doc('B2C Settings')

    if not solr:
        solr_url = doc.get('solr_url')
        solr = pysolr.Solr(solr_url)

    return solr

def get_image_uri_instance():
    """Get the Solr image instance from the B2C Settings DocType"""

    global image_uri

    if not image_uri:
        doc = frappe.get_doc('B2C Settings')
        image_uri = doc.get('image_uri')

    return image_uri


@frappe.whitelist(allow_guest=True, methods=['GET'])
def shop(args=None):
    # Call the catalogue function with the given arguments
    return catalogue(args)


@frappe.whitelist(allow_guest=True, methods=['GET'])
def catalogue(args=None):
    # Get the "start" and "per_page" parameters from the query string
    per_page = int(frappe.local.request.args.get('per_page', 12) or 12 ) 
    page = int(frappe.local.request.args.get('page') or 1)
    page = page - 1 if page > 0 else 0
    start = page*per_page
    text = frappe.local.request.args.get('search_term') or '*'

    # Construct the Solr query to search for text
    query = f'text:{text}'

    order_by = frappe.local.request.args.get('order_by')

    # Construct the Solr search parameters
    search_params = {
        'q': query,
        'start': start,
        'rows': per_page,
    }

    # Sort the search results based on the value of the "order_by" parameter
    if order_by == 'price-asc':
        search_params['sort'] = 'prezzo asc'
    elif order_by == 'price-desc':
        search_params['sort'] = 'prezzo desc'

    # Get the Solr instance from the B2C Settings DocType
    solr = get_solr_instance()

    # Execute the search and get the results
    search_results = solr.search(**search_params)

    # Get the total number of search results
    count = search_results.hits

    # Calculate the number of pages
    pages = int((count + per_page - 1) / per_page)

    # Check if this is the last page
    is_last = (start + per_page >= count)

    # Extract the search results from the response
    search_results = [dict(result) for result in search_results]

    search_results_mapped = map_solr_response_b2c(search_results)

    # Construct the response
    response =  {
        'totalCount': count,
        'current_page': page + 1,
        'pages': pages,
        'per_page': per_page,
        'is_last':is_last,
        'products': search_results_mapped,
        'solr_result' : search_results,
        'query': query
    }
    return response


    # Return the response with HTTP 200 status
    # return response.values()


def map_solr_response_b2c(search_results):
    # Define the mapping between Solr and our response
    field_mapping = {
        'id': 'id',
        'oarti': 'id',
        'carti': 'carti',
        'carti': 'sku',
        'name': 'name',
        'prezzo': 'price',
        'prezzo_iniziale': 'sale_price',
        'name_web':'short_description',
        'promo':'is_sale',
        'disponibilita':'stock',
        'images': 'immagini',
        'slug':'slug'
    }

    # Get the Solr image instance URI
    image_uri = get_image_uri_instance()

    # Initialize the mapped results list
    mapped_results = []

    # Map the Solr results to our desired format
    for result in search_results:
        mapped_result = get_default_product_values()  # Add default values
        for solr_field, response_field in field_mapping.items():
            # Skip fields that are not present in the Solr result
            if solr_field not in result:
                continue
            if solr_field == 'images':
                # Map the image URLs
                images = get_image_sizes(result, image_uri)
                mapped_result.update(images)
            else:
                mapped_result[response_field] = result[solr_field]

        if mapped_result['sale_price'] > 0:
            # Swap price and sale_price if prezzo_iniziale exists and is greater than 0
            mapped_result['price'] = result['prezzo_iniziale']
            mapped_result['sale_price'] = result['prezzo']
        else:
            mapped_result['sale_price'] = None

        # Map additional fields
        if 'id_group' in result:
            mapped_result['product_categories'] = []
            for category in result['id_group']:
                mapped_category = {
                    'nome': category,
                    'slug': category ,
                    'parent': category['parent_name'] if 'parent_name' in category else None
                }
                mapped_result['product_categories'].append(mapped_category)

        if 'product_brands' in result:
            mapped_result['marche'] = []
            for brand in result['product_brands']:
                mapped_brand = {
                    'nome': brand['name'],
                    'slug': brand['slug']
                }
                mapped_result['marche'].append(mapped_brand)

        if 'product_tags' in result:
            mapped_result['tags'] = []
            for tag in result['product_tags']:
                mapped_tag = {
                    'nome': tag['name'],
                    'slug': tag['slug']
                }
                mapped_result['tags'].append(mapped_tag)

        if 'variants' in result:
            mapped_result['varianti'] = []
            for variant in result['variants']:
                mapped_variant = {
                    'id': variant['id'],
                    'prezzo': variant['price'],
                    'prezzo_scontato': variant['sale_price'] if 'sale_price' in variant else None
                }
                if 'size' in variant:
                    mapped_variant['taglia'] = []
                    for size in variant['size']:
                        mapped_size = {
                            'nome': size['size_name'],
                            'valore': size['size']
                        }
                        mapped_variant['taglia'].append(mapped_size)

                if 'colors' in variant:
                    mapped_variant['colori'] = []
                    for color in variant['colors']:
                        mapped_color = {
                            'nome': color['color_name'],
                            'valore': color['color']
                        }
                        mapped_variant['colori'].append(mapped_color)

                mapped_result['varianti'].append(mapped_variant)

        mapped_results.append(mapped_result)

    return mapped_results


def get_image_sizes(result, image_uri):
    """
    Get image URLs for different sizes from Solr result
    """
    images = {
        'large_pictures': [],
        'small_pictures': [],
        'gallery_pictures': [],
        'main_pictures': []
    }
    image_sizes = {
        'large_pictures': {
            'prefix': '',
            'width': '1000',
            'height': '1000'
        },
        'small_pictures': {
            'prefix': 'thumb_',
            'width': '150',
            'height': '150'
        },
        'gallery_pictures': {
            'prefix': 'gallery_',
            'width': '350',
            'height': '350'
        },
        'main_pictures': {
            'prefix': 'main_',
            'width': '800',
            'height': '800'
        }
    }
    
    for image_size in image_sizes:
        size_data = image_sizes[image_size]
        size_prefix = size_data['prefix']
        size_width = size_data['width']
        size_height = size_data['height']
        size_images = []

        for image in result['images']:
            size_images.append({
                'url': image_uri + '/' + result['id'] + '/' + size_prefix + image,
                'width': size_width,
                'height': size_height
            })

        images[image_size] = size_images
    
    return images

def get_default_product_values():
    return {
        'sale_count': 0,
        'ratings': 0,
        'reviews': "0",
        'is_hot': True,
        'is_new': True,
        'is_out_of_stock': None,
        'release_date': None,
        'developer': None,
        'publisher': None,
        'game_mode': None,
        'rated': None,
        'until': None,
        'variants': []
    }



@frappe.whitelist(allow_guest=True)
def products():
    # Get the Solr instance from the B2C Settings DocType
    solr = get_solr_instance()

    # Get the slug parameter from the query string
    slug = frappe.local.request.args.get('slug')

    # Check if the slug parameter is present in the query string
    if not slug:
        frappe.throw(_('Slug parameter is missing'), frappe.ValidationError)

    # Construct the Solr query to search for the product based on its slug
    query = f'slug:{slug}'

    # Construct the Solr search parameters
    search_params = {
        'q': query,
        'rows': 1,
    }

    # Execute the search and get the results
    search_results = solr.search(**search_params)

    # Check if there are any search results
    if search_results.hits == 0:
        frappe.throw(_('Product not found'), frappe.DoesNotExistError)

    # Extract the product details from the Solr result
    product = map_solr_response_b2c([dict(search_results.docs[0])])[0]

    # Construct the response
    response =  {
        'product': product,
    }

    # Return the response with HTTP 200 status
    return response


