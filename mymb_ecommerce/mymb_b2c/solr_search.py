
from mymb_ecommerce.mymb_b2c.settings.media import Media
from mymb_ecommerce.mymb_b2c.settings.configurations import Configurations
import frappe
from frappe import _

config = Configurations()
solr_instance = config.get_solr_instance()
image_uri_instance = config.get_image_uri_instance()

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
    groups = frappe.local.request.args.get('category') or None
    features = frappe.local.request.args.get('features') or None

   # Construct the Solr query to search for text and filter by non-empty "slugs" field
    query = f'text:{text} AND -slug:("")'

    # Check if min_price is provided in the query string and add it to the query if it is
    min_price = frappe.local.request.args.get('min_price')
    if min_price and float(min_price) > 0:
        query += f'AND prezzo:[{min_price} TO *]'

    # Check if max_price is provided in the query string and add it to the query if it is
    max_price = frappe.local.request.args.get('max_price')
    if max_price and float(max_price) > 0:
        query += f'AND prezzo:[* TO {max_price}]'

    order_by = frappe.local.request.args.get('order_by')

    # Construct the Solr search parameters
    search_params = {
        'q': query,
        'start': start,
        'rows': per_page,
        'stats': 'true',
        'stats.field': 'prezzo'
    }

    if groups:
       search_params["groups"]=groups 
    
    if features:
        search_params["features"]=features

    # Sort the search results based on the value of the "order_by" parameter
    if order_by == 'price-asc':
        search_params['sort'] = 'prezzo asc'
    elif order_by == 'price-desc':
        search_params['sort'] = 'prezzo desc'

    # Get the Solr instance from the Configurations class
    solr = solr_instance

    # Execute the search and get the results
    solr_results = solr.search(**search_params)

    # Get the total number of search results
    count = solr_results.get('hits')

    # Get the minimum and maximum prices of all products
    solr_full_response = solr_results.get('response')
    stats = solr_full_response.stats
    price_stats = stats.get('stats_fields', {}).get('prezzo', {})
    min_price_all = price_stats.get('min')
    max_price_all = price_stats.get('max')

    # Calculate the number of pages
    pages = int((count + per_page - 1) / per_page)

    # Check if this is the last page
    is_last = (start + per_page >= count)

    # Extract the search results from the response
    search_results = [dict(result) for result in solr_results['results']]

    # Get the image uri instance from the Configurations class

    search_results_mapped = map_solr_response_b2c(search_results)

    # Construct the response
    facet = solr_results.get('facet_counts')
    if facet:
        category = facet.get('category')
        features = facet.get('features')
    response =  {
        'totalCount': count,
        'current_page': page + 1,
        'pages': pages,
        'per_page': per_page,
        'is_last':is_last,
        'products': search_results_mapped,
        'solr_result' : search_results,
        'query': query,
        'min_price_all': int(min_price_all) if min_price_all is not None else None,
        'max_price_all': int(max_price_all) if max_price_all is not None else None,
        "category": category,
        "features": features
    }
    return response


def map_solr_response_b2c(search_results ):
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


    # Initialize the mapped results list
    mapped_results = []

    # Map the Solr results to our desired format
    media = Media(image_uri_instance)
    for result in search_results:
        mapped_result = get_default_product_values()  # Add default values
        for solr_field, response_field in field_mapping.items():
            # Skip fields that are not present in the Solr result
            if solr_field not in result:
                continue
            if solr_field == 'images':
                # Map the image URLs
                images = media.get_image_sizes(result)
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
    # Get the Solr instance from the Mymb b2c Settings DocType
    solr = solr_instance

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
    solr_results = solr.search(**search_params)

    # Check if there are any search results
    if solr_results['hits'] == 0:
        frappe.throw(_('Product not found'), frappe.DoesNotExistError)

    # Extract the product details from the Solr result
    product = map_solr_response_b2c([dict(solr_results['results'][0])])[0]

    # Construct the response
    response =  {
        'product': product,
    }

    # Return the response with HTTP 200 status
    return response


