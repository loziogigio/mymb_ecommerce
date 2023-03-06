from typing import Any, Dict, List, Optional, Tuple
from mymb_ecommerce.mymb_b2c.settings.configurations import Configurations

import frappe
import requests
from frappe import _

JsonDict = Dict[str, Any]


class MymbB2cItem:
    """Return item from b2c 


	"""
    def __init__(self):
        """Start Solr configuration."""
        self.solr = Configurations().get_solr_instance()
        self.image_uri = Configurations().get_image_uri_instance()

    def get_mymb_b2c_item(self, sku: str, log_error=True) -> Optional[JsonDict]:
        """Get MymbAPIClient item data for specified SKU code. """
        item, status = self._get_item_by_carti(sku)
        if status:
            return item

    def _get_item_by_carti(self, carti: str) -> Tuple[Optional[JsonDict], bool]:
        """Get MymbAPIClient item data by its 'carti' code (SKU).

		"""
		# Construct the Solr query to search for the product based on its SKU (carti)
        query = f'carti:"{carti}"'

		# Construct the Solr search parameters
        search_params = {
            'q': query,
            'rows': 1,
            'fl': '*,score'
        }

        # Execute the search and get the results
        solr_results = self.solr.search(**search_params)

        # Check if there are any search results
        if solr_results['hits'] == 0:
            return None, False

        # Extract the product details from the Solr result
        product = dict(solr_results['results'].docs[0])

		# Add image URLs to the product details
        if product['num_images'] > 0:
            # Get the image file name
            image_file_name = product['images'][0]

            # Construct the image URL
            image_url = f'{self.image_uri}/{image_file_name}'

            # Add the image URL to the product details
            product['image_url'] = image_url

		# Return the product details
        return product, True