import pysolr
from urllib.parse import quote
import re

class Solr:
    def __init__(self, url, **kwargs):
        self.solr = pysolr.Solr(url, **kwargs)

    def search(self, q, start=0, rows=10, sort=None, groups=None, features=None, **kwargs):
        """
        Execute a Solr search query and return the results.

        :param q: str - The query string.
        :param start: int - The starting index of the search results (default: 0).
        :param rows: int - The number of search results to return (default: 10).
        :param sort: str - The sorting criteria for the search results (default: None).
        :param groups: str - The comma-separated list of group values (default: None).
        :param facet_fields: list - The fields to facet on (default: None).
        :param **kwargs: Additional Solr query parameters as keyword arguments.
        :return: dict - A dictionary containing the search results and facet counts.
        """
        params = {
            'q': q,
            'start': start,
            'rows': rows
        }

        if sort:
            params['sort'] = sort
        
        if groups:
            group_list = groups.split(',')

            params['facet'] = 'on'
            params['facet.field'] = f'group_{len(group_list)+1}'
            params['facet.mincount'] = 1

            fq_list = [f'group_{i+1}:"{group.replace("-", " ")}"' for i, group in enumerate(group_list)]
            params['fq'] = fq_list
        else:
            params['facet'] = 'on'
            params['facet.field'] = 'group_1'
            params['facet.mincount'] = 1


        params.update(kwargs)

        response = self.solr.search(**params)

        # Get the search results
        results = [dict(result) for result in response]

         # Get the facet counts
        facet_counts = Solr.get_facet(response=response,groups=groups, features=features)


        # Return the results and facet counts as a dictionary
        return {
            'results': results,
            'facet_counts': facet_counts,
            'hits': response.hits,
            'response': response
        }
    
    @staticmethod
    def get_feature_suffix(feature_type):
        """
        Helper function to accept the feature type and return the appropriate suffix.
        Supported feature types are: 'int', 'float', and 'string'.
        Returns None if the feature type is not recognized.
        """
        if feature_type == 'int':
            return '_feature_i'
        elif feature_type == 'float':
            return '_feature_f'
        elif feature_type == 'string':
            return '_feature_s'
        else:
            return None


    @staticmethod
    def get_facet(response, groups, features):
        # Get the facet counts
        facet_counts = {
            "categories": [],
            "features": []
        }
        if 'facet_counts' in response.raw_response:
            for field, counts in response.raw_response['facet_counts']['facet_fields'].items():
                if field.startswith("group"):
                    # Use "categories" as the field name for group fields
                    field = "categories"
                    facet_counts[field] = [{'label': label, 'count': count, "url": f"{groups},{label.replace(' ', '-')}" if groups else label.replace(' ', '-')} for label, count in zip(counts[::2], counts[1::2])]
                else:
                    # Extract the facet name from the field name for feature fields
                    match = re.match(r'(.*)_feature_(\w)', field)
                    if match:
                        clean_field = match.group(1).replace(" ", "-")
                        label_field = match.group(1)
                        feature_type = match.group(2)

                        facet_results = [{"value": value, "count": count} for value, count in zip(counts[::2], counts[1::2])]

                        facet_counts["features"].append({
                            "clean_field": clean_field,
                            "label_field": label_field,
                            "type": feature_type,
                            "facet_results": facet_results
                        })
                    # For other fields, use the original field name
                    else:
                        pass

        return facet_counts

    
    @staticmethod
    def clean_feature_name(feature_name):
        """
        Helper function to clean a feature name and escape any special characters for Solr.
        Removes leading and trailing whitespace, tabs, and newlines.
        Replaces any remaining whitespace with a single space.
        Replaces any commas with a space.
        Escapes any special characters with a backslash to ensure Solr can interpret them correctly.
        Returns the cleaned and escaped feature name.
        """
        # Remove leading and trailing whitespace, tabs, and newlines
        cleaned_name = feature_name.strip()
        
        # Replace any remaining whitespace with a single space
        cleaned_name = re.sub(r'\s+', ' ', cleaned_name)
        
        # Replace any commas with a space
        cleaned_name = cleaned_name.replace(",", " ")

        # Escape any special characters for Solr
        cleaned_name = re.sub(r'([\[\]!"#$%&\'()*+,\-./:;<=>?@\^_`{|}~])', r'\\\1', cleaned_name)

        return cleaned_name
    

    @staticmethod
    def get_feature_suffix(feature_type):
        """
        Helper function to accept the feature type and return the appropriate suffix.
        Supported feature types are: 'int', 'float', and 'string'.
        Returns None if the feature type is not recognized.
        """
        if feature_type == 'int':
            return '_feature_i'
        elif feature_type == 'float':
            return '_feature_f'
        elif feature_type == 'string':
            return '_feature_s'
        else:
            return None