import pysolr
from urllib.parse import quote
import re
import frappe
import xml.etree.ElementTree as ET
import requests
import json
import math
# from mymb_ecommerce.repository.FeatureRepository import FeatureRepository
# Generate a random seed for shuffling
import random

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
        
        # Ensure 'fq' exists in params
        params['fq'] = []

        if groups:
            group_list = groups.split(',')

            params['facet'] = 'on'
            params['facet.mincount'] = 1

            fq_list = [f'group_{i+1}:"{group.replace("-", " ")}"' for i, group in enumerate(group_list)]
            params['fq'] = fq_list

            group_facet_fields = [f'group_{i+1}' for i in range(len(group_list) + 1)]
            
            params['facet.field'] = group_facet_fields
            
        else:
            params['facet'] = 'on'
            params['facet.field'] = ['group_1']
            params['facet.mincount'] = 1

        #whne we ae going to have just one family_Coe we wil do the faceting
        params['facet.field'].append('family_code')



        # Feature Filters Section
        # -----------------------
        # Initialize feature filters as an empty list
        feature_filters = []
        feature_dict= None

        # Parse the JSON-encoded features into a dictionary
        # Check if features is not None and then parse the JSON-encoded features into a dictionary
        if features:
            try:
                feature_dict = json.loads(features)
            except json.JSONDecodeError as e:
                print(f"Error decoding features: {e}")
                feature_dict = {}

        # If the feature dictionary is not empty, construct the feature filters
        if feature_dict:
            for key, value in feature_dict.items():
                # Create the Solr filter query (fq) for each feature
                feature_filter = f'{key}:"{value}"'
                feature_filters.append(feature_filter)

        # Add feature filters to the 'fq' parameter
        if feature_filters:
            params['fq'].extend(feature_filters)

        # Family Code and Family Name Filters
        # -----------------------------------
        # Check if family_code is in params and add it to the fq parameter
        family_code = kwargs.get('family_code')
        if family_code:
            if isinstance(family_code, list):
                if len(family_code) == 1:
                    family_code_filter = f"family_code:{family_code[0]}"
                else:
                    family_code_filter = f"family_code:({' '.join(map(str, family_code))})"
            else:
                family_code_filter = f"family_code:{family_code}"

            params['fq'].append(family_code_filter)

        # Check if family_name is in params and add it to the fq parameter
        family_name = kwargs.get('family_name')
        if family_name:
            family_name_filter = f"family_name:{family_name[0]}"
            params['fq'].append(family_name_filter)

        # Random Sorting Section
        # ----------------------
        # Check if random sorting is required and apply random seed-based sorting
        is_random = kwargs.get('is_random')
        if 'sort' not in params and is_random:
            random_seed = random.randint(0, 1000000)
            params['sort'] = f'random_{random_seed} asc'
                

        # params.update(kwargs)

        # search_array = ["sku", "name_nostem"]

        # search_array = ["sku","name" , "name_nostem"]  # Add more fields if needed

        search_array = ["sku", "name_nostem","name", "short_description_nostem","short_description","description_nostem","description"]  # Add more fields if needed
        boost_factors = self.calculate_exp_boost_factors(search_array) # Boost factors for each type of search




        # Check if the query includes 'text:' and handle it accordingly
        # Improved regex to handle edge cases
        match = re.search(r'text:(.*?)(?: AND| OR|$)', q)

        if match:
            # Extract the value after 'text:'
            search_term = match.group(1)
            # Build the boosted query
            boosted_query = self.build_boosted_query(search_term, search_array, boost_factors)

            # Remove the 'text:value' part from the original query
            q = re.sub(r'text:.*?( AND| OR|$)', r'\1', q).strip()
            # Combine the original query with the boosted query
            final_query = f'({boosted_query}) {q}'
        else:
            # Use boosted query for queries not including 'text:'
            final_query = q


        params['q'] = final_query

        response = self.solr.search(**params)

        # Get the search results
        results = [dict(result) for result in response]

        # Get the facet counts
        facet_counts = Solr.get_facet(response=response, groups=groups, features=features)

        # If family_code has more than one array object, add dynamic facet fields
        family_code_list = facet_counts.get("family_code", [])
        if len(family_code_list) == 1:
            family_features = self.get_dynamic_facet_fields_by_family_code( family_code_list[0] )
            # Ensure family_features is not empty
            if len(family_features) > 0:
                # Iterate over the family_features and append the keys (facet field names)
                for family_feature_key, family_feature_value in family_features.items():
                    # Append the key to the params['facet.field']
                    params['facet.field'].append(family_feature_key)

                response_facet_family_features = self.solr.search(**params)
                # Get the facet counts
                facet_counts = Solr.get_facet(response=response_facet_family_features, groups=groups, features=family_features)

        return {
            'results': results,
            'facet_counts': facet_counts,
            'hits': response.hits,
            'response': response
        }
    
    def build_advanced_query(self, query, search_array, term_boost, phrase_boost):
        """
        Build an advanced query for partial and phrase matches.

        :param query: str - The search query, e.g., 'alb nat'.
        :param search_array: list - List of fields to search in.
        :param term_boost: int - Boost factor for individual term matches.
        :param phrase_boost: int - Boost factor for the entire phrase match.
        :return: str - The advanced query.
        """
        terms = query.split()
        term_queries = []
        phrase_query = '"' + query + '"'

        # Construct queries for individual terms
        for term in terms:
            for field in search_array:
                term_queries.append(f'{field}:{term}*^{term_boost}')

        # Construct a phrase query
        phrase_queries = [f'{field}:{phrase_query}^{phrase_boost}' for field in search_array]

        # Combine all queries
        combined_query = ' OR '.join(term_queries + phrase_queries)
        return combined_query

    def calculate_exp_boost_factors(self, search_array, base_boost=1 , base=5):
        """
        Calculate exponential boost factors for fields in the search array.

        :param search_array: list - List of fields to search in.
        :param base_boost: int - The base boost factor (multiplier for the exponentiation).
        :return: list - List of calculated boost factors.
        """
        boost_factors = [base_boost * math.pow(base, index + 1) for index in range(len(search_array))]

        return boost_factors
    
    def build_boosted_query(self, query, search_array, boost_factors):
        """
        Build a boosted query based on the search array and boost factors.

        :param query: str - The search query, e.g., 'text:Ryža NER'.
        :param search_array: list - List of fields to search in.
        :param boost_factors: list - List of boost factors for each search type.
        :return: str - The boosted query.
        """
        search_term = query.split(':', 1)[1].strip() if ':' in query else query.strip()
        tokens = search_term.split()
        boosted_queries = []
        boosted_query_tuples = []

        for i, field in enumerate(search_array):
            boost_index = len(boost_factors) - i - 1

            if len(tokens) > 1:
                # Exact match for multi-token
                exact_match_query = f'{field}:"{search_term}"'
                boosted_query_tuples.append((exact_match_query, boost_factors[boost_index]*3))

                # Start with condition for each token combined
                start_with_combined_query = ' AND '.join([f'{field}:{token}*' for token in tokens])
                boosted_query_tuples.append((start_with_combined_query, boost_factors[boost_index]*2))

                # End with condition for each token combined
                end_with_combined_query = ' AND '.join([f'{field}:*{token}' for token in tokens])
                boosted_query_tuples.append((end_with_combined_query, boost_factors[boost_index]))

                # Contains condition for each token combined
                contains_combined_query = ' AND '.join([f'{field}:*{token}*' for token in tokens])
                boosted_query_tuples.append((contains_combined_query, boost_factors[boost_index]))
            else:
                # Conditions for single token
                exact_match_query = f'{field}:"{search_term}"'
                boosted_query_tuples.append((exact_match_query, boost_factors[boost_index]*3))

                starts_with_query = f'{field}:{search_term}*'
                boosted_query_tuples.append((starts_with_query, boost_factors[boost_index]*3))

                ends_with_query = f'{field}:*{search_term}'
                boosted_query_tuples.append((ends_with_query, boost_factors[boost_index]))

                contains_query = f'{field}:*{search_term}*'
                boosted_query_tuples.append((contains_query, boost_factors[boost_index]))

        # Sort by boost factor in descending order
        boosted_query_tuples.sort(key=lambda x: x[1], reverse=True)

        # Construct the final query string using formatted tuples
        boosted_queries = [f'({query_str})^{boost}' for query_str, boost in boosted_query_tuples]

        return ' OR '.join(boosted_queries)

        # # Sort by boost factor in descending order
        # boosted_query_tuples.sort(key=lambda x: x[1], reverse=True)

        # # Construct the final query string using formatted tuples
        # boosted_queries = [f'{query_str}^{boost}' for query_str, boost in boosted_query_tuples]






    def escape_solr_query(self, query):
        """
        Escape special characters in the Solr query.

        :param query: str - The query to escape.
        :return: str - The escaped query.
        """
        special_chars = ['+', '-', '&', '|', '!', '(', ')', '{', '}', '[', ']', '^', '"', '~', '*', '?', ':', '\\']
        escaped_query = "".join([f'\\{char}' if char in special_chars else char for char in query])
        return escaped_query.replace(' ', '\\ ')
    
    
    
    @staticmethod
    def get_dynamic_facet_fields_by_family_code( family_code ):
        """
        Search for Feature Families with the family_code equal to the given family_code.
        :param family_code: str - The family_code value.
        :return: list - The dynamic facet fields based on the family_code.
        """
        # Normalize the family_code (replace dashes with spaces and convert to lowercase)
        from mymb_ecommerce.repository.FeatureRepository import FeatureRepository
        feature_repo = FeatureRepository()
        # Fetch feature families based on the family_code
        feature_families = {}
        # Use the FeatureRepository to fetch features by family_code
        family_features = feature_repo.get_features_by_family_id_b2c(family_code.get("code" , 0))
        

        return family_features

    def get_dynamic_facet_fields(self, group):
        """
        Search for Feature Families with the family_code equal to group.
        :param group: str - The group value.
        :return: list - The dynamic facet fields based on the group.
        """
        group = group.replace("-", " ").lower()
        feature_families = {}

        family_response = frappe.db.sql(
            """SELECT * FROM `tabFeature Family` WHERE LOWER(family_name) = %s""",
            (group,),
            as_dict=True,
        )
        
        feature_families[group] = []

        for family in family_response:
            feature_name_query = {
                'doctype': 'Feature Name',
                'filters': {'name': family['feature_name']},
                'fields': ['name', 'feature_type', 'feature_label']
            }
             
            feature_name_response = frappe.get_all(**feature_name_query)

            for feature_name in feature_name_response:
                feature_type = feature_name["feature_type"]
                feature_label = feature_name["feature_label"]
                feature_suffix = Solr.get_feature_suffix(feature_type)
                feature_field = f'{Solr.clean_feature_name(feature_label)}{feature_suffix}'
                feature_families[group].append(feature_field)

        # Merge feature fields from all groups
        merged_feature_fields = []
        for fields in feature_families.values():
            merged_feature_fields.extend(fields)

        return merged_feature_fields
 
    def has_subgroups(self, group_counter, group):
        """
        Check if a group has any subgroups.

        :param group_counter: int - The current group counter.
        :param group: str - The group value to check.
        :return: bool - True if the group has subgroups, False otherwise.
        """
        group_query = f'group_{group_counter}:"{group.replace("-"," ")}"'
        facet_field = f'group_{group_counter + 1}'
        response = self.solr.search(q=group_query, rows=0, facet='on', facet_field=facet_field, facet_mincount=1)

        facet_counts = response.raw_response['facet_counts']['facet_fields'].get(facet_field, [])
        return len(facet_counts) > 0

    def commit(self):
        """
        Commit changes in the Solr index.
        :return: dict - A dictionary representing the Solr response.
        """
        try:
            self.solr.commit()
            # Return a JSON-compatible response
            return {"status": "success"}
        except pysolr.SolrError as e:
            print(f"Commit failed: {e}")
            return {"status": "failure", "reason": str(e)}

    def add_documents(self, docs):
        """
        Add a list of documents to the Solr index.

        :param docs: list - A list of dictionaries representing the documents to be added.
        :return: dict - A dictionary representing the Solr response.
        """
        if not isinstance(docs, list):
            raise ValueError("docs should be a list of dictionaries.")
        try:
            self.solr.add(docs)
            # Return a JSON-compatible response
            return {"status": "success", "documents_added": len(docs)}
        except pysolr.SolrError as e:
            print(f"Add documents failed: {e}")
            return {"status": "failure", "reason": str(e)}

    def update_document(self, doc):
        """
        Update a document in the Solr index. If the document does not exist, it will be created.

        :param doc: dict - A dictionary representing the document to be updated.
        :return: dict - A dictionary representing the Solr response.
        """
        if not isinstance(doc, dict):
            raise ValueError("doc should be a dictionary.")
            
        # Prepare document for atomic update
        atomic_doc = {"id": doc["id"]}
        for field, value in doc.items():
            if field != "id":
                atomic_doc[field] = {"set": value}
        
        return self.add_documents([atomic_doc])  # leverage the add_documents method for updates


    def delete_document(self, id):
        """
        Delete a document from the Solr index.

        :param id: str - The unique identifier of the document to be deleted.
        :return: dict - A dictionary representing the Solr response.
        """
        if not isinstance(id, str):
            raise ValueError("id should be a string.")
        try:
            self.solr.delete(id=id)
            # Return a JSON-compatible response
            return {"status": "success", "id": id}
        except pysolr.SolrError as e:
            print(f"Request failed: {e}")
            return {"status": "failure", "reason": str(e)}
    
    def delete_all_documents(self):
        """
        Delete all documents from the Solr index.

        :return: dict - A dictionary representing the Solr response.
        """
        try:
            self.solr.delete(q='*:*')  # Delete all documents
            return {"status": "success", "message": "All documents deleted"}
        except pysolr.SolrError as e:
            print(f"Request failed: {e}")
            return {"status": "failure", "reason": str(e)}


    @staticmethod
    def get_facet(response, groups, features):
        # Get the facet counts
        facet_counts = {
            "category": [],
            "features": [],
            "family_code": [],
        }
        if 'facet_counts' in response.raw_response:
            for field, counts in response.raw_response['facet_counts']['facet_fields'].items():
                if field.startswith("group"):
                    # Use "categories" as the field name for group fields
                    field = "category"
                    facet_counts[field] = [{'label': label, 'count': count, "url": f"{groups},{label.replace(' ', '-')}" if groups else label.replace(' ', '-')} for label, count in zip(counts[::2], counts[1::2])]
                elif field == 'family_code':
                    # Handle family_code specifically
                    facet_counts["family_code"] = [{'code': code, 'count': count} for code, count in zip(counts[::2], counts[1::2])]
                else:
                    # Extract the facet name from the field name for feature fields
                    match = re.match(r'(.*)_feature_(\w)', field)
                    if match:
                        
                        facet_results = [{"value": value, "count": count} for value, count in zip(counts[::2], counts[1::2])]
                        feature = features[field]
                        # Skip the feature if there are no facet results
                        if not facet_results:
                            continue

                        facet_counts["features"].append({
                            "key": field,
                            "label_field": feature.get('label',''),
                            "type": feature.get('feature_type',''),
                            "facet_results": facet_results,
                            "uom" : feature.get('uom_id','')
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
    def unclean_feature_name(escaped_name):
        """
        Helper function to reverse the changes applied by clean_feature_name.
        Unescapes any special characters.
        Replaces hyphens with spaces.
        Returns the original feature name.
        """
        # Unescape any special characters
        unescaped_name = re.sub(r'\\([\[\]!"#$%&\'()*+,\-./:;<=>?@\^_`{|}~])', r'\1', escaped_name)

        # Replace hyphens with spaces
        original_name = unescaped_name.replace('-', ' ')

        return original_name

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
        elif feature_type == 'date':
            return '_feature_dt'
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
                
