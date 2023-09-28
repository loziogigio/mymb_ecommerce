import frappe
from mymb_ecommerce.repository.TmpCarrelloRepository import TmpCarrelloRepository
from mymb_ecommerce.utils.MymbAPIClient import MymbAPIClient
from datetime import datetime




@frappe.whitelist(allow_guest=True, methods=['POST'])
def get_cart_list(limit=None, time_laps=None, page=1, filters=None,  sort_by = "data_registrazione", fetch_property=False, fetch_media=False, fetch_price=False , sort_order=None):
    # Map the external filter keys to internal ones
    filter_mapping = {
        'client_id': 'id_cliente',
        'id_cart': 'id_carrello',
        'status': 'stato'
    }
    
    if filters:
        filters = {filter_mapping.get(key, key): value for key, value in filters.items()}

    # Initialize the TmpCarrelloRepository
    tmp_cart_repo = TmpCarrelloRepository()

    # Fetch all the TmpCarrello items from the external database
    tmp_cart_list = tmp_cart_repo.get_all_records_b2b(limit=limit, page=page, time_laps=time_laps, filters=filters, sort_by=sort_by , to_dict=True , sort_order=sort_order)

    return {
        "data": tmp_cart_list,
        "count": len(tmp_cart_list)
    }
