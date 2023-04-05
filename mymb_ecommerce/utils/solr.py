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
        
        # Add dynamic fields for faceting
        # dynamic_facet_fields = ["*_feature_i", "*_feature_f", "*_feature_s", "*_feature_b"]
        
        #let's do some static features to have some results
        dynamic_facet_fields = ["marca_feature_s","marca_feature_s","lunghezza_feature_i","altezza_feature_i","peso_feature_f","forma_feature_s",]

        if groups:
            group_list = groups.split(',')

            params['facet'] = 'on'
            params['facet.mincount'] = 1

            fq_list = [f'group_{i+1}:"{group.replace("-", " ")}"' for i, group in enumerate(group_list)]
            params['fq'] = fq_list

            # Combine the group facet fields with the dynamic facet fields
            group_facet_fields = [f'group_{i+1}' for i in range(len(group_list) + 1)]
            params['facet.field'] = group_facet_fields + dynamic_facet_fields
        else:
            params['facet'] = 'on'
            params['facet.field'] = ['group_1'] + dynamic_facet_fields
            params['facet.mincount'] = 1

        feature_filters = Solr.get_features(features)


        # Add the feature filters to the fq parameter
        if 'fq' not in params:
            params['fq'] = []
        params['fq'].extend(feature_filters)

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
            "category": [],
            "features": []
        }
        if 'facet_counts' in response.raw_response:
            for field, counts in response.raw_response['facet_counts']['facet_fields'].items():
                if field.startswith("group"):
                    # Use "categories" as the field name for group fields
                    field = "category"
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
                            "key": clean_field,
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
        cleaned_name = re.sub(r'\s+', '-', cleaned_name)

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
        elif feature_type == 'boolean':
            return '_feature_b'
        else:
            return None

    # Parse the features argument
    @staticmethod
    def get_features(features):
        """
        Helper function to parse the features argument and build the list of filters.
        :param features: str - The comma-separated list of features and their values (e.g. "lunghezza=488,marca=bestway").
        :return: list - A list of feature filters for the Solr query.
        """
        if features:
            feature_filters = []
            feature_list = features.split(',')
            for feature in feature_list:
                field, value = feature.split('=')
                field = field.strip()
                # Get the feature type from the field
                feature_type = Solr.detect_feature_type(value)

                if feature_type:
                    # Get the feature suffix based on the feature type
                    feature_suffix = Solr.get_feature_suffix(feature_type)

                    # Add the feature filter to the list
                    field_with_suffix = f'{field}{feature_suffix}'
                    feature_filters.append(f'{field_with_suffix}:"{value}"')
                else:
                    raise ValueError(f"Unable to detect feature type for field '{field}' with value '{value}'")

            return feature_filters
        else:
            return None

    @staticmethod
    def detect_feature_type(value):
        """
        Helper function to detect the feature type based on the value.
        :param value: str - The value of the feature.
        :return: str - The detected feature type ('int', 'float', 'string', or 'boolean').
        """
        try:
            int(value)
            return 'int'
        except ValueError:
            try:
                float(value)
                return 'float'
            except ValueError:
                if value.lower() == 'true' or value.lower() == 'false':
                    return 'boolean'
                else:
                    return 'string'
