import frappe
from frappe import _
from mymb_ecommerce.utils.solr import Solr
from mymb_ecommerce.utils.database import Database

class Configurations:
    def __init__(self):
        self.doc = frappe.get_doc('Mymb b2c Settings')
        self.image_uri = self.doc.get('image_uri')
        #solr section
        self.solr_url = self.doc.get('solr_url')
        self.mymb_b2c_payment_success_page =  self.doc.get('mymb_b2c_payment_success_page')
        self.mymb_b2c_payment_failed_page=  self.doc.get('mymb_b2c_payment_failed_page')
        self.solr = None
        #mysql section
        # self.mysql_settings = self.doc.get('mysql_settings').as_dict()
        # self.mysql_connection = None

    def get_solr_instance(self):
        """Get the Solr instance from the Mymb b2c Settings DocType"""

        if not self.solr:
            self.solr = Solr(self.solr_url)

        return self.solr

    def get_image_uri_instance(self):
        """Get the Solr image instance from the Mymb b2c Settings DocType"""

        return self.image_uri
    
    def get_mymb_b2c_payment_success_page(self):
        """Get Success payment page from the Mymb b2c Settings DocType"""

        return self.mymb_b2c_payment_success_page

    def get_mymb_b2c_payment_failed_page(self):
        """Get Failed payment page from the Mymb b2c Settings DocType"""

        return self.mymb_b2c_payment_failed_page
    
    # def get_mysql_connection(self):
    #     """Get the MySQL connection from the Mymb b2c Settings DocType"""

    #     if not self.mysql_connection:
    #         self.mysql_connection = Database(self.mysql_settings)

    #     return self.mysql_connection
