import base64
from typing import Any, Dict
import frappe
import requests
from frappe import _
from frappe.utils.password import get_decrypted_password
from mymb_ecommerce.mymb_b2c.constants import SETTINGS_DOCTYPE
from mymb_ecommerce.utils.MymbAPIClient import MymbAPIClient
from mymb_ecommerce.repository.MytrridoRepository import MytrridoRepository
from mymb_ecommerce.mymb_b2c.settings.configurations import Configurations
from omnicommerce.controllers.pdf import create_folder_structure
from datetime import datetime
import os
from frappe.utils.file_manager import save_file_on_filesystem
import uuid

JsonDict = Dict[str, Any]

@frappe.whitelist(allow_guest=True, methods=['POST'])  # Changed to 'GET' as you're fetching data
def get_document(causale, anno, numero , order_name):
    config = Configurations()
    mytrridoRepository = MytrridoRepository()

    # Create the filter document with the provided filters
    filter_document = {
        'ccaus_sdocu_2': causale,
        'ycale_xxxxx_2': anno,
        'nprot_ddocu_2': numero
    }

    # Fetch the document information using the filters
    document_info = mytrridoRepository.get_record_by_filters(**filter_document)

    if not document_info:
        # Create the filter document for invoices
        filter_document_invoice = {
            'ccaus_sdocu_1': causale,
            'ycale_xxxxx_1': anno,
            'nprot_ddocu_1': numero
        }
        # Fetch the document information using the filters
        document_info = mytrridoRepository.get_record_by_filters(**filter_document_invoice)

    if not document_info:
        frappe.throw(_("Document not found with the given filters."))

    base_url = config.url_doc_public_service  # Ensure this returns something like "http://example.com/"

    # Construct the full URL with query parameters
    full_url = f"{base_url}web/GetFileArchiviatoFromPkDoc?Causale={document_info.ccaus_sdocu_4}&Anno={document_info.ycale_xxxxx_4}&Numero={document_info.nprot_ddocu_4}&TipoDocumento="

    # Make the GET request
    try:
        response = requests.get(full_url)
        if response.status_code == 200:
            response_data = response.json()
            data = response_data.get("GetFileArchiviatoFromPkDocResult")
            
            if data:
                contenuto = data.get("Contenuto")
                nome = data.get("Nome")

                if contenuto and nome:
                    # Decode the base64 content
                    pdf_content = base64.b64decode(contenuto)
                    # Generate a unique folder name
                    unique_folder_name = f"Home/Attachments"
                    # Save the PDF file
                    file_url = save_pdf_file(pdf_content, nome, "Sales Order", order_name, unique_folder_name)
                    return {"file_url": file_url}
                else:
                    frappe.throw(_("Failed to get valid content or file name from the response."))

        else:
            frappe.throw(_("Failed to fetch the document. Status code: {0}").format(response.status_code))
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "get_invoice_service Failed")
        frappe.throw(_("Failed to fetch the document due to an error: {0}").format(e))

def save_pdf_file(pdf_content: bytes, file_name: str, attached_to_doctype: str, attached_to_name: str, folder: str) -> str:
    """
    Save the PDF content to a file and create a File document in Frappe.

    :param pdf_content: The binary content of the PDF file.
    :param file_name: The name of the PDF file.
    :param attached_to_doctype: The doctype to which the file is attached.
    :param attached_to_name: The name of the document to which the file is attached.
    :param folder: The folder where the file will be saved.
    :return: The URL of the saved file.
    """
    # Check if folder exists, if not create it
    create_folder_structure(folder)

    # Check if the file already exists
    # Check if the file already exists using a SQL-like wildcard search
    existing_file = frappe.db.sql("""
        SELECT file_url
        FROM `tabFile`
        WHERE file_name LIKE %s AND attached_to_name = %s AND attached_to_doctype = %s
    """, (f"%-{file_name}", attached_to_name, attached_to_doctype), as_dict=True)

    if existing_file:
        return existing_file[0]["file_url"]

    # Create a unique file name
    unique_file_name = f"{uuid.uuid4()}-{file_name}"

    # Save the file on the filesystem
    file_doc = frappe.get_doc({
        "doctype": "File",
        "file_name": unique_file_name,
        "content": pdf_content,
        "folder": folder,
        "is_private": 0,
        "attached_to_doctype": attached_to_doctype,
        "attached_to_name": attached_to_name
    })

    # Save the File document
    file_doc.save(ignore_permissions=True)

    # Commit the changes to the database
    frappe.db.commit()

    return file_doc.file_url
