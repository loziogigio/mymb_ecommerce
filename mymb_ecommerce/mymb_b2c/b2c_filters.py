
import frappe
from datetime import datetime
from frappe import _

@frappe.whitelist(allow_guest=True, methods=['GET'])
def get_province():
    """
    Fetch distinct province codes and their names.
    Returns a list of tuples containing (codice_provincia, provincia).
    """
    # SQL query to select distinct province codes and names
    data = frappe.db.sql("""
        SELECT DISTINCT `codice_provincia`, `provincia`
        FROM `tabCap`
        ORDER BY `codice_provincia`
    """, as_dict=True)
    
    # Return the result as a list of dictionaries
    return data

import frappe

@frappe.whitelist(allow_guest=True)
def get_zipcode(province_code=""):
    """
    Fetch all postal codes (CAP) for a given province code.
    Args:
    province_code (str): The province code to filter CAPs by.

    Returns:
    list of dict: A list containing the postal codes for the given province code.
    """
    if not province_code:
        # If no province code is provided, return an empty list or all CAPs (decide based on use case)
        return []
    
    # SQL query to select CAPs for the specified province code
    get_zipcodes = frappe.db.sql("""
        SELECT comune,cap,provincia, regione, codice_provincia
        FROM `tabCap`
        WHERE `codice_provincia` = %s
    """, (province_code,), as_dict=True)
    
    return get_zipcodes

