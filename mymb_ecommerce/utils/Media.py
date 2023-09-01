import os


class Media:

    def __init__(self, image_uri):
        self.image_uri = image_uri


    def get_image_sizes(self, result , prefix_thumb='thumb_',prefix_gallery='gallery_' ,prefix_main='main_' ):
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
                'prefix': prefix_thumb,
                'width': '150',
                'height': '150'
            },
            'gallery_pictures': {
                'prefix': prefix_gallery,
                'width': '350',
                'height': '350'
            },
            'main_pictures': {
                'prefix': prefix_main,
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

                base_path=''
                if self.image_uri:
                    base_path = self.image_uri + '/'

                size_images.append({
                    'url': base_path + new_image_path,
                    'width': size_width,
                    'height': size_height
                })

            images[image_size] = size_images
        
        return images
    

    def get_image_suffix(self, result , suffix_thumb='_s',suffix_gallery='_m' ,suffix_main='_l' ):
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
                'suffix': '',
                'width': '1000',
                'height': '1000'
            },
            'small_pictures': {
                'suffix': suffix_thumb,
                'width': '200',
                'height': '200'
            },
            'gallery_pictures': {
                'suffix': suffix_gallery,
                'width': '400',
                'height': '400'
            },
            'main_pictures': {
                'suffix': suffix_main,
                'width': '1200',
                'height': '1200'
            }
        }
        
        for image_size in image_sizes:
            size_data = image_sizes[image_size]
            size_suffix = size_data['suffix']
            size_width = size_data['width']
            size_height = size_data['height']
            size_images = []

            for image in result['images']:
                # Split the image filename and its extension
                image_name, image_extension = os.path.splitext(image)
                
                # Append the size_suffix to the image_name and then re-add the extension
                url_image = f"{image_name}{size_suffix}{image_extension}"
 


                size_images.append({
                    'url': url_image,
                    'width': size_width,
                    'height': size_height
                })

            images[image_size] = size_images

        return images



