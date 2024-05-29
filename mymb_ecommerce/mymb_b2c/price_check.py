import frappe
from frappe import _
from mymb_ecommerce.mymb_b2c.item import get_items_from_external_db
from typing import List, Dict, Any



def check_if_any_promotion(items_code: List[Any]) -> bool:
    # Extract the item codes from the list of QuotationItem objects
    item_codes_list = [item.item_code for item in items_code]
    
    # Generate the filter string for the API call
    filters = {'carti':item_codes_list}
    
    # Retrieve items from the external database
    items = get_items_from_external_db(
        limit=None, 
        time_laps=None, 
        page=1,  
        filters=filters, 
        fetch_property=False, 
        fetch_media=False, 
        fetch_price=True, 
        fetch_categories=False
    )
    
    # Check for promotions in the retrieved items
    if not items or not items.get('data'):
        return False
    
    for item in items.get('data'):
        prices = item.get('prices', {})
        if prices.get('is_best_promo', False) or prices.get('is_promo', False):
            return True
    
    return False