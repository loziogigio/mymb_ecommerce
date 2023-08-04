
from mymb_ecommerce.utils.Media import Media
from mymb_ecommerce.mymb_b2c.settings.configurations import Configurations
from mymb_ecommerce.mymb_ecommerce.item_feature import get_features_by_item_name, map_feature_with_uom_via_family_code
from mymb_ecommerce.mymb_ecommerce.item_review import get_item_reviews
from mymb_ecommerce.mymb_ecommerce.wishlist import get_from_wishlist
from mymb_ecommerce.repository.DataRepository import DataRepository
from mymb_ecommerce.utils.media import get_website_domain
import frappe
from frappe import _

from mymb_ecommerce.utils.JWTManager import JWTManager, JWT_SECRET_KEY
jwt_manager = JWTManager(secret_key=JWT_SECRET_KEY)


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
    whishlist = frappe.local.request.args.get('wishlist') or None
    home = frappe.local.request.args.get('home') or None
    category_detail = frappe.local.request.args.get('category_detail') or None

    wishlist_items = []  # Initialize wishlist_items variable

    #we just search for whishlist
    if whishlist:
        JWTManager.verify_jwt_in_request()
        wishlist_items = get_from_wishlist(user=frappe.local.jwt_payload['email'])

    if wishlist_items:
        item_codes = [item['item_code'] for item in wishlist_items]
        query = f'text:{text} AND ({" OR ".join([f"carti:{code}" for code in item_codes])})'
    else:
        query = f'text:{text}'

    if home:
        query = f'text:piscina' 

    # Check if min_price is provided in the query string and add it to the query if it is
    min_price = frappe.local.request.args.get('min_price')
    if min_price and float(min_price) > 0:
        query += f' AND net_price_with_vat:[{min_price} TO *]'

    # Check if max_price is provided in the query string and add it to the query if it is
    max_price = frappe.local.request.args.get('max_price')
    if max_price and float(max_price) > 0:
        query += f' AND net_price_with_vat:[* TO {max_price}]'

    # Check if min_discount_value is provided in the query string and add it to the query if it is
    min_discount_value = frappe.local.request.args.get('min_discount_value')
    if min_discount_value and float(min_discount_value) > 0:
        query += f' AND discount_value:[{min_discount_value} TO *]'

    # Check if max_discount_value is provided in the query string and add it to the query if it is
    max_discount_value= frappe.local.request.args.get('max_discount_value')
    if max_discount_value and float(max_discount_value) > 0:
        query += f' AND discount_value:[* TO {max_discount_value}]'

    # Check if min_discount_percent is provided in the query string and add it to the query if it is
    min_discount_percent = frappe.local.request.args.get('min_discount_percent')
    if min_discount_percent and float(min_discount_percent) > 0:
        query += f' AND discount_percent:[{min_discount_percent} TO *]'

    # Check if max_discount_percent is provided in the query string and add it to the query if it is
    max_discount_percent= frappe.local.request.args.get('max_discount_percent')
    if max_discount_percent and float(max_discount_percent) > 0:
        query += f' AND discount_percent:[* TO {max_discount_percent}]'

    order_by = frappe.local.request.args.get('order_by')

    # Construct the Solr search parameters
    search_params = {
        'q': query,
        'start': start,
        'rows': per_page,
        'stats': 'true',
        'stats.field': 'net_price_with_vat'
    }

    if groups:
       search_params["groups"]=groups 
    
    if features:
        search_params["features"]=features

    # Sort the search results based on the value of the "order_by" parameter
    if order_by == 'price-asc':
        search_params['sort'] = 'net_price_with_vat asc'
    elif order_by == 'price-desc':
        search_params['sort'] = 'net_price_with_vat desc'

    # Get the Solr instance from the Configurations class
    solr = solr_instance

    # Execute the search and get the results
    solr_results = solr.search(**search_params)

    # Get the total number of search results
    count = solr_results.get('hits')

    # Get the minimum and maximum prices of all products
    solr_full_response = solr_results.get('response')
    stats = solr_full_response.stats
    price_stats = stats.get('stats_fields', {}).get('net_price_with_vat', {})
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
        #We have map features with their uom
        features = map_feature_with_uom_via_family_code(features , search_results_mapped)
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
        "features": features,
        "menu_category_detail": get_menu_category_detail(category_detail)
    }
    return response

def get_menu_category_detail(category_detail):
    web_site_domain = get_website_domain()
    try:
        # This will fetch specific fields of the document where label matches `menu_category`
        doc_dict = frappe.get_doc("B2C Menu", {"label": category_detail})
        # Filter the doc_dict to include only the desired keys
        filtered_dict = {
            'name': doc_dict.get('name'),
            'label': doc_dict.get('label'),
            'url': doc_dict.get('url'),
            'title': doc_dict.get('title'),
            'description': doc_dict.get('description'),
            'category_menu_image': f'{web_site_domain}{doc_dict.get("category_menu_image")}' if doc_dict.get("category_menu_image") else None,
            'category_banner_image': f'{web_site_domain}{doc_dict.get("category_banner_image")}' if doc_dict.get("category_banner_image") else None
        }
        

        return filtered_dict

    except frappe.DoesNotExistError:
        # Handle the case where no document matches the provided `menu_category`
        return None


def map_solr_response_b2c(search_results ):
    # Define the mapping between Solr and our response
    field_mapping = {
        'id': 'id',
        'sku': 'sku',
        'name': 'name',
        'gross_price_with_vat': 'gross_price',
        'net_price_with_vat': 'net_price',
        'promo_price_with_vat': 'promo_price',
        'name_web':'short_description',
        'is_promo':'is_sale',
        'availability':'stock',
        'images': 'images',
        'slug':'slug',
        'family_code':'family_code'
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

        if mapped_result['is_sale']  and mapped_result['promo_price'] > 0 :
            # Swap price and sale_price if prezzo_iniziale exists and is greater than 0
            mapped_result['price'] = result['gross_price_with_vat']
            mapped_result['sale_price'] = result['promo_price_with_vat']
        else:
            mapped_result['sale_price'] = None
            mapped_result['price'] = result['net_price_with_vat']

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

    product["short_description"] = "short description text"
    product["long_description"] = '<div><span style="font-family: inherit;">Piscina intex ultra frame 26326 con struttura progettata per massimizzare la stabilità e la robustezza grazie ai pratici tubi ovali e agli innovativi 3 strati di pvc antitaglio.</span><br></div><div>Il pool liner ultra frame della piscina intex 26326 è realizzato con pareti resistenti a 3 strati, 3 volte più resistenti delle piscine tradizionali ed è composto da uno strato retinato in poliestere contenuto tra due spessi strati di pvc antitaglio.</div><div>Per assicurare robustezza e solidità, la struttura è realizzata con tubi extra robusti che grazie alla propria forma ovale garantiscono al cliente finale un risultato senza paragoni in termini di stabilità ed affidabilità.</div><div>La piscina intex ultra frame 26326 ha al suo interno 2 raccordi da collegare alla pompa di filtrazione corredata con un diametro di 38mm.</div><div><br></div><div><b>Specifiche tecniche:</b></div><div><br></div><div><div>peso articolo: 90.6 chilogrammi</div><div>dimensioni 488 x 122 cm (diametro x altezza)</div><div><div><span style="font-family: inherit;">materiale: pvc triplice strato</span><br></div><div>materiale telaio: acciaio verniciato a polvere</div><div>colore: grigio scuro</div></div><div>capacità 19156 litri al 90%</div><div>tempo di montaggio 1 ora</div></div><div><br></div><div><b>Accessori inclusi nella piscina ultra frame intex 26326:</b></div><div><br></div><div>pompa di filtraggio intex 4 m3/h (26644)</div><div>scala di sicurezza</div><div>telo di copertura</div><div>tappeto sottopiscina</div><div><br></div><div><b>Marca:</b> Intex</div><div><b>Modello:</b> 26326</div>'

    args = frappe._dict()
    args.family_code = 1009
    relatedProducts = catalogue(args)

    product["features"] = get_features_by_item_name(product["sku"])
    
    data_repo = DataRepository()
    data = data_repo.get_data_by_entity_code(product["id"])
    # Convert data into a format suitable for your use case (e.g., a list of dictionaries)
    product_data = {row.property_id: row.value for row in data}
    product['product_data'] = product_data

    product['long_description'] = product_data.get('long_description', '')
    product['short_description'] = product_data.get('short_description', '')
    product['item_reviews'] = get_item_reviews(product["sku"])



    # Construct the response
    response =  {
        'product': product,
        'relatedProducts': relatedProducts['products'],
        'featuredProducts': relatedProducts['products'],
        'bestSellingProducts': relatedProducts['products'],
        'latestProducts': relatedProducts['products'],
        'topRatedProducts': relatedProducts['products'],
    }

    # Return the response with HTTP 200 status
    return response





