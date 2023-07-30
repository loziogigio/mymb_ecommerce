import frappe
from frappe import _
from mymb_ecommerce.utils.Solr import Solr
from mymb_ecommerce.utils.Database import Database
from frappe.utils.password import get_decrypted_password


class Configurations:
    def __init__(self):
        self.doc = frappe.get_doc('Mymb Settings')
        self.image_uri = self.doc.get('image_uri')
        #solr section
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
        """Get Success payment page from the Mymb b2c Settings DocType"""

        return self.mymb_b2c_payment_failed_page
    
    

    def get_mysql_connection(self):
        """Get the MySQL connection from the Mymb b2c Settings DocType"""
        if not hasattr(self, 'mysql_connection'):
            username = self.doc.get('db_username')
            db_password = get_decrypted_password("Mymb Settings", self.doc.name, 'db_password')  # Decrypt the password
            db_host = self.doc.get('db_host')
            db_port = self.doc.get('db_port')
            db_mymb_item = self.doc.get('db_item_data')
            db_mymb_transaction = self.doc.get('db_item_data')


            db_config = {
                'drivername': 'mysql',
                'username': username,
                'password': db_password,
                'host': db_host,
                'port': db_port,
                'database': db_mymb_item
            }
            self.mysql_connection = Database(db_config)

        return self.mysql_connection
