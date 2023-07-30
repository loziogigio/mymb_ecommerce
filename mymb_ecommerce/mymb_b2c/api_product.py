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
        item, status = self._get_item_by_sku(sku)
        if status:
            return item

    def _get_item_by_sku(self, sku: str) -> Tuple[Optional[JsonDict], bool]:
        """Get MymbAPIClient item data by its 'sku' code (SKU).

		"""
		# Construct the Solr query to search for the product based on its SKU (sku)
        query = f'sku:"{sku}"'

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
        product = dict(solr_results['results'][0])

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
    
    def get_item_batch_by_offset(self, batch_size: int, offset: int) -> List[JsonDict]:
        """
        Get MymbAPIClient items in batches using the Solr 'start' parameter.

        :param batch_size: The size of each batch.
        :param offset: The offset of the first item to retrieve.
        :return: A list of MymbAPIClient items.
        """
        items = []

        while True:
            # Construct the Solr query to search for products
            query = 'carti:*'

            # Construct the Solr search parameters
            search_params = {
                'q': query,
                'rows': batch_size,
                'start': offset,
                'fl': '*,score'
            }

            try:
                # Execute the search and get the results
                solr_results = self.solr.search(**search_params)

                # Check if there are any search results
                if solr_results['hits'] == 0:
                    break

                # Extract the products from the Solr result
                products = [dict(result) for result in solr_results['results']]

                # Add image URLs to the products details
                for product in products:
                    if product['num_images'] > 0:
                        # Get the image file name
                        image_file_name = product['images'][0]

                        # Construct the image URL
                        image_url = f'{self.image_uri}/{image_file_name}'

                        # Add the image URL to the product details
                        product['image_url'] = image_url

                # Add the products to the items list
                items.extend(products)

                # If the number of retrieved items is less than the batch size, then all items have been retrieved
                if len(products) < batch_size:
                    break

                # Increment the offset to retrieve the next batch of items
                offset += batch_size

            except Exception as e:
                # Log any errors and return the retrieved items
                frappe.log_error(_('Error retrieving items from Solr: {0}').format(str(e)))
                break

        return items

    def get_mymb_b2c_item_count(self) -> int:
        """Get the total count of items in Mymb B2c."""
        query = 'carti:*'
        search_params = {
            'q': query,
            'rows': 0,
        }
        solr_results = self.solr.search(**search_params)
        return solr_results["hits"]

