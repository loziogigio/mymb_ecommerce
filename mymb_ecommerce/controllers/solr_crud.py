from mymb_ecommerce.mymb_b2c.settings.configurations import Configurations
from mymb_ecommerce.utils.Database import Database
import frappe
from frappe import _
from sqlalchemy import text
import json
from mymb_ecommerce.utils.Solr import Solr

config = Configurations()
solr_instance = config.get_solr_instance()
image_uri_instance = config.get_image_uri_instance()

# Add the following imports at the beginning of your filestatu


import json
import frappe

@frappe.whitelist(allow_guest=True, methods=['POST'])
def add_document_to_solr(args=None):
    """
    Add a document to the Solr index.

    :return: dict - A dictionary representing the Solr response.
    """


    # Get the Solr instance from the Configurations class
    solr = solr_instance

    # Add the document to Solr
    response = solr.add_documents([args])
    solr.commit()

    # Return the response
    return response

@frappe.whitelist(allow_guest=True, methods=['POST'])
def delete_document_to_solr(id=None):
    """
    Delete a document from the Solr index using the given id.

    :return: dict - A dictionary representing the Solr response.
    """
    if not id:
        return {"error": "No id provided"}

    # Get the Solr instance from the Configurations class
    solr = solr_instance

    # Delete the document from Solr
    response = solr.delete_document(id=id)
    solr.commit()

    # Return the response
    return response

@frappe.whitelist(allow_guest=True, methods=['POST'])
def update_document_in_solr(args=None):
    """
    Update a document in the Solr index.

    :return: dict - A dictionary representing the Solr response.
    """


    # Get the Solr instance from the Configurations class
    solr = solr_instance

    # Update the document in Solr
    response = solr.update_document(args)
    solr.commit()

    # Return the response
    return response

@frappe.whitelist(allow_guest=True, methods=['POST'])
def delete_all_solr_docs():
    """
    Delete all documents from the Solr index.

    :return: dict - A dictionary representing the Solr response.
    """

    # Get the Solr instance from the Configurations class
    solr = solr_instance

    # Delete all documents from Solr
    response = solr.delete_all_documents()
    solr.commit()

    # Return the response
    return response

