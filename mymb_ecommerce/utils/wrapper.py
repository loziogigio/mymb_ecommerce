# For product_list

def paginate(items, per_page=5, total=None, page=None, pages=None, options=None):
    if not items:
        return None

    pagination = {
        'data': items,
        'pagination': {
            'current_page': page,
            'total': total,
            'pages': pages
        }
    }

    return pagination

def build_product_list(product_array):
    result_array = []

    # Continue processing the dictionary as usual

    if 'prices' in product_array and isinstance(product_array['prices'], dict):
        # Access 'listino_type' if it's a dictionary
        product_array['prices']['listino_type'] = product_array['prices'].get('listino_type', '')
    else:
        # Handle the case where 'prices' is not a dictionary
        product_array['prices'] = {
            'listino_type': product_array.get('listino_type', ''),
            'listino_code': product_array.get('listino_code', '')
        }

    if product_array:
      for id, value in product_array['results'].items():
         wrapped_data = wrap_product_detail_from_list(value, product_array['prices'])
         if wrapped_data:
            result_array.append(wrapped_data)

      return result_array

def wrap_product_detail_from_list(data, prices):
    prices_data_id = {}
    price_discount = None
    is_sale = False
    
    if data['id'] in prices:
        prices_data_id = prices[data['id']]
        is_sale = prices_data_id.get('price_discount', 0) > 0
        price_discount = prices_data_id.get('price_discount', None)
        # Check if 'all_promo' key exists in prices_data_id
        # Check if 'all_promo' key exists in prices_data_id
        if 'all_promo' in prices_data_id:
            # Iterate through each promo in all_promo list
            for promo in prices_data_id['all_promo']:
                # Add 'promo_row' key to each promo with value from 'RigaPromozione'
                promo['promo_row'] = promo['RigaPromozione']

            # Update prices_data_id with the modified all_promo list
            prices_data_id['all_promo'] = prices_data_id['all_promo']


    result = {
        'developer': None,
        'game_mode': None,
        'id': data['id'],
        'is_hot': False,
        'is_new': data['new'],
        'is_out_of_stock': None,
        'is_sale': is_sale,
        'large_pictures': [
            {
                'width': 800,
                'height': 800,
                'url': data['image'],
            }
        ],
        'name': data['title'],
        'pictures': [
            {
                'width': 300,
                'height': 300,
                'url': data['image'],
            }
        ],
        'price': data['default_price'],
        'product_brands': [],
        'product_categories': [],
        'product_tags': [],
        'publisher': None,
        'rated': None,
        'ratings': 0,
        'release_date': None,
        'reviews': "0",
        'sale_count': 0,
        'sale_price': price_discount,
        'short_description': data['short_descr'],
        'sku': data['carti'],
        'slug': data['id'],
        'small_pictures': [
            {
                'width': 300,
                'height': 300,
                'url': data['image'],
            }
        ],
        'stock': 54,
        'until': None,
        'variants': [],
        'num_childs': data['numChilds'],
        'childs': data['childs'],
        'prices': prices if prices else {},
        'stato': data.get('stato', None),
        'extra_info': {**data, **prices_data_id},
    }

    return result

def build_filter_list(erp_data):
  
   result = {
      'facets_results': erp_data['facets_results'],
      'facets_link_results': erp_data['facets_link_results'],
      'facets_check_results': erp_data.get('facets_check_results ',[]),
   }
   return result


def wrap_product_detail(data):

    prices = data.get('prices', {}) or {}
    product_id = data['product']['id']
    price_info = prices.get(product_id, {})
    promo = price_info.get('promo', False)
    
    

    
    result = {
        'developer': None,
        'game_mode': None,
        'id': data['product']['id'],
        "is_single_child": data['product']['is_single_child'],
        'is_hot': False,
        'is_new': None,
        'is_out_of_stock': None,
        'is_sale': promo,
        'large_pictures': build_picture_array(data['product']['images'], 800, 800),
        'name': data['product']['title'],
        'pictures': build_picture_array(data['product']['images'], 300, 300),
        'price': data['product']['default_price'],
        'product_brands': data['product']['brand'],
        'product_categories': [],
        'product_tags': [],
        'publisher': None,
        'rated': None,
        'ratings': 0,
        'release_date': None,
        'reviews': "0",
        'sale_count': 0,
        'sale_price': data['product']['default_price'],
        'short_description': data['product']['short_descr'],
        'sku': data['product']['carti'],
        'codice_figura': data['product']['codice_figura'],
        'id_father': data['product']['id_father'],
        'slug': data['product']['id'],
        'small_pictures': build_picture_array(data['product']['images'], 150, 150),
        'stock': 54,
        'until': None,
        'variants': [],
        'price_info': price_info,
        'promo_list': data['promo'],
        'extra_info': data,
        'listino_type': data.get('listino_type', None),
        'listino_code': data.get('listino_code', None),
    }

    # Adding 'is_rate_promo' key for conditions met in 'all_promo' list
    all_promo_list = price_info.get('all_promo', [])
    for promo in all_promo_list:
        if promo.get("TipoPromozione") == "RigaPrezzoNettoQuantitaMinima":
            promo['is_rate_promo'] = True
        else:
            promo['is_rate_promo'] = False

    return result

def wrap_child_product_detail(data):
    prices = data.get('prices', {}) or {}
    result = {
        'developer': None,
        'game_mode': None,
        "is_single_child": data['data']['is_single_child'],
        'id': data['data']['id'],
        'codice_figura': data['data']['codice_figura'],
        'id_father': data['data']['father_id'],
        'is_hot': False,
        'is_new': None,
        'is_out_of_stock': None,
        'is_sale': prices.get('promo', False),
        'large_pictures': build_picture_array(data['data']['images'], 800, 800),
        'name': data['data']['title'],
        'pictures': build_picture_array(data['data']['images'], 300, 300),
        'price': prices.get('price', None),
        'product_brands': [],
        'product_categories': [],
        'product_tags': [],
        'publisher': None,
        'rated': None,
        'ratings': 0,
        'release_date': None,
        'reviews': "0",
        'sale_count': 0,
        'sale_price': prices.get('price_discount', None),
        'short_description': data['data']['long_descr'],
        'sku': data['data']['carti'],
        'slug': data['data']['id'],
        'small_pictures': build_picture_array(data['data']['images'], 150, 150),
        'stock': 54,
        'until': None,
        'variants': [],
        'price_info': prices,
        'listino_type': data.get('listino_type', None),
        'listino_code': data.get('listino_code', None),
        'promo_list': data['promo'],
        'extra_info': data,
    }

    # Adding 'is_rate_promo' key for conditions met in 'all_promo' list
    all_promo_list = result.get('price_info', {}).get('all_promo', [])
    for promo in all_promo_list:
        if promo.get("TipoPromozione") == "RigaPrezzoNettoQuantitaMinima":
            promo['is_rate_promo'] = True
        else:
            promo['is_rate_promo'] = False

    return result


def build_picture_array(image_array, width, height):
    result_array = []
    for url in image_array:
        result_array.append({
            'width': width,
            'height': height,
            'url': url,
        })
    return result_array
