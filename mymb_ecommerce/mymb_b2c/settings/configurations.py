import frappe
from frappe import _
from mymb_ecommerce.utils.Solr import Solr
from mymb_ecommerce.utils.Database import Database
from frappe.utils.password import get_decrypted_password


# Singleton pattern: Cache Configurations instance per site for B2C
_b2c_configurations_cache = {}


def get_b2c_configurations_instance():
    """
    Get or create B2C Configurations instance for current site.
    Uses singleton pattern to ensure connection pools are shared.
    """
    site = getattr(frappe.local, 'site', 'default')

    if site not in _b2c_configurations_cache:
        _b2c_configurations_cache[site] = Configurations()

    return _b2c_configurations_cache[site]


class Configurations:
    def __init__(self):
        self.doc = frappe.get_doc('Mymb b2c Settings')
        self.image_uri = self.doc.get('image_uri')
        #solr section
        self.enable_mymb_b2c = self.doc.get('enable_mymb_b2c')
        self.transfer = self.doc.get('transfer')
        self.cash_on_delivery = self.doc.get('cash_on_delivery')
        self.paypal = self.doc.get('paypal')
        self.credit_card = self.doc.get('credit_card')
        self.solr_url = self.doc.get('solr_url')
        self.b2c_url = self.doc.get('b2c_url')
        self.customer_code = self.doc.get('customer_code')
        self.customer_address_code = self.doc.get('customer_address_code')
        self.mymb_b2c_payment_success_page =  self.doc.get('mymb_b2c_payment_success_page')
        self.mymb_b2c_payment_failed_page=  self.doc.get('mymb_b2c_payment_failed_page')
        self.mymb_b2c_wire_transfer =   self.doc.get('wire_transfer')
        self.default_item_group =   self.doc.get('default_item_group')
        self.b2c_title =   self.doc.get('b2c_title')
        self.email_b2c =   self.doc.get('email_b2c')
        self.emails_confirm_sales_order_on_submit =   self.doc.get('emails_confirm_sales_order_on_submit')
        self.confirm_sales_order_html_template =   self.doc.get('confirm_sales_order_html_template')
        self.confirm_sales_order_transfer_html_template =   self.doc.get('confirm_sales_order_transfer_html_template')
        self.confirm_sales_order_cash_on_delivery_html_template = self.doc.get('confirm_sales_order_cash_on_delivery_html_template') 
        self.stripe_api_endpoint =   self.doc.get('stripe_api_endpoint')
        self.gestpay_api_endpoint =   self.doc.get('gestpay_api_endpoint')
        self.solr = None
        self.send_confirmation_email_to_admin = self.doc.get('send_confirmation_email_to_admin')
        self.order_shipped_label = self.doc.get('order_shipped_label')
        self.channel_id_lablel = self.doc.get('channel_id_lablel')
        self.sync_the_last_number_of_days = self.doc.get('sync_the_last_number_of_days')
        self.url_doc_public_service = self.doc.get('url_doc_public_service')
        
        #mysql section
        # self.mysql_settings = self.doc.get('mysql_settings').as_dict()
        # self.mysql_connection = None

    def get_solr_instance(self):
        """Get the Solr instance from the Mymb b2c Settings DocType"""

        if not self.solr:
            self.solr = Solr(self.solr_url)

        return self.solr


    def get_mymb_b2c_wire_transfer(self):
        """Get the MyMb b2c transfer"""

        return self.mymb_b2c_wire_transfer

   

    def get_image_uri_instance(self):
        """Get the Solr image instance from the Mymb b2c Settings DocType"""

        return self.image_uri
    
    def get_mymb_b2c_payment_success_page(self):
        """Get Success payment page from the Mymb b2c Settings DocType"""

        return self.mymb_b2c_payment_success_page
    
    def get_mymb_b2c_payment_failed_page(self):
        """Get Success payment page from the Mymb b2c Settings DocType"""

        return self.mymb_b2c_payment_failed_page
    
    def get_mymb_b2c_customer_code(self):
        """Get default customer_code for b2c """

        return self.customer_code
    

    def get_mymb_b2c_customer_address_code(self):
        """Get default customer_address_code for b2c """

        return self.customer_address_code
    
    

    def get_mysql_connection(self , is_data_property=True, is_db_transaction=False , is_erp_db=False ):
        """Get the MySQL connection from the Mymb b2c Settings DocType"""
        if not hasattr(self, 'mysql_connection'):
            username = self.doc.get('db_username')
            db_password = get_decrypted_password("Mymb b2c Settings", self.doc.name, 'db_password')  # Decrypt the password
            db_host = self.doc.get('db_host')
            db_port = self.doc.get('db_port')
            if is_db_transaction:
                db_name = self.doc.get('db_transactions')
            elif is_erp_db:
                db_name = self.doc.get('db_erp')
            elif is_data_property:
                db_name = self.doc.get('db_item_data')

            db_config = {
                'drivername': 'mysql',
                'username': username,
                'password': db_password,
                'host': db_host,
                'port': db_port,
                'database': db_name
            }
            self.mysql_connection = Database(db_config)

        return self.mysql_connection
    
    def get_mysql_generic_connection(self , is_data_property=True, is_db_transaction=False , is_erp_db=False ):
        """Get the MySQL connection from the Mymb b2c Settings DocType"""
        if not hasattr(self, 'mysql_connection'):
            username = self.doc.get('db_username')
            db_password = get_decrypted_password("Mymb b2c Settings", self.doc.name, 'db_password')  # Decrypt the password
            db_host = self.doc.get('db_host')
            db_port = self.doc.get('db_port')

            db_config = {
                'drivername': 'mysql',
                'username': username,
                'password': db_password,
                'host': db_host,
                'port': db_port
            }
            self.mysql_connection = Database(db_config)

        return self.mysql_connection

