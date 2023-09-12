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
   product_array['prices']['listino_type'] = product_array.get('listino_type', '')
   product_array['prices']['listino_code'] = product_array.get('listino_code', '')

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
