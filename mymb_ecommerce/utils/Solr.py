import pysolr
from urllib.parse import quote
import re
import frappe
import xml.etree.ElementTree as ET
import requests
import json


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
            params['facet.mincount'] = 1

            fq_list = [f'group_{i+1}:"{group.replace("-", " ")}"' for i, group in enumerate(group_list)]
            params['fq'] = fq_list

            group_facet_fields = [f'group_{i+1}' for i in range(len(group_list) + 1)]
            
             # Fetch dynamic facet fields based on group faceting
            last_group = group_list[-1]
            if not self.has_subgroups(len(group_list),last_group):
                dynamic_facet_fields = self.get_dynamic_facet_fields(last_group)
            else:
                dynamic_facet_fields = []

            params['facet.field'] = group_facet_fields + dynamic_facet_fields
        else:
            params['facet'] = 'on'
            params['facet.field'] = ['group_1']
            params['facet.mincount'] = 1

        # Initialize feature filters as an empty list
        feature_filters = Solr.get_features(features)

        # Add the feature filters to the fq parameter
        if 'fq' not in params:
            params['fq'] = []
        if feature_filters is not None:
            params['fq'].extend(feature_filters)

        params.update(kwargs)

        response = self.solr.search(**params)

        # Get the search results
        results = [dict(result) for result in response]

        # Get the facet counts
        facet_counts = Solr.get_facet(response=response, groups=groups, features=features)

        # Return the results and facet counts as a dictionary
        return {
            'results': results,
            'facet_counts': facet_counts,
            'hits': response.hits,
            'response': response
        }

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
                        
                        # Skip the feature if there are no facet results
                        if not facet_results:
                            continue

                        facet_counts["features"].append({
                            "key": clean_field,
                            "label_field": Solr.unclean_feature_name(label_field),
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
                
