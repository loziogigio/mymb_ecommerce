
import frappe
from datetime import datetime
from frappe import _

@frappe.whitelist(allow_guest=True, methods=['GET'])
def get_regions():
    """
    Return distinct list of regions (regione) from the Cap table.
    """
    regions = frappe.db.sql("""
        SELECT DISTINCT regione
        FROM `tabCap`
        WHERE regione IS NOT NULL AND regione != ''
        ORDER BY regione
    """, as_dict=True)
    return regions


@frappe.whitelist(allow_guest=True, methods=['GET'])
def get_province(region=""):
    """
    Fetch distinct province codes and their names, optionally filtered by region.
    Args:
        region (str): Optional region name to filter by.
    Returns:
        list of dict: A list of provinces with fields 'codice_provincia' and 'provincia'.
    """
    if region:
        data = frappe.db.sql("""
            SELECT DISTINCT `codice_provincia`, `provincia`
            FROM `tabCap`
            WHERE `regione` = %s
            ORDER BY `codice_provincia`
        """, (region,), as_dict=True)
    else:
        data = frappe.db.sql("""
            SELECT DISTINCT `codice_provincia`, `provincia`
            FROM `tabCap`
            ORDER BY `codice_provincia`
        """, as_dict=True)

    return data


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

