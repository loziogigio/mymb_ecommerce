import frappe
import requests
import os


class Media:

    def __init__(self, image_uri):
        self.image_uri = image_uri


    def get_image_sizes(self, result):
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
                dir_name, file_name = os.path.split(image)
                new_file_name = size_prefix + file_name
                new_image_path = os.path.join(dir_name, new_file_name)

                size_images.append({
                    'url': self.image_uri + '/' + new_image_path,
                    'width': size_width,
                    'height': size_height
                })

            images[image_size] = size_images
        
        return images

