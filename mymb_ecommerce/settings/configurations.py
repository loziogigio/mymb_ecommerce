import frappe
from frappe import _
from mymb_ecommerce.utils.Solr import Solr
from mymb_ecommerce.utils.Database import Database
from frappe.utils.password import get_decrypted_password
from mymb_ecommerce.utils.CircuitBreaker import CircuitBreaker


class Configurations:
    # Conservative DB connection pool limits for ALL tenants to prevent worker blocking
    # Smaller pools = one tenant's DB issues won't exhaust all connections
    DEFAULT_POOL_SIZE = 3  # Max 3 concurrent DB connections per tenant
    DEFAULT_MAX_OVERFLOW = 5  # Allow up to 5 extra in bursts

    def __init__(self):
        self.doc = frappe.get_doc('Mymb Settings')
        self.image_uri = self.doc.get('image_uri')
        self.solr_mymb_backoffice = self.doc.get('solr_mymb_backoffice')
        self.solr_url = self.doc.get('solr_url')
        self.mymb_payment_success_page = self.doc.get('mymb_payment_success_page')
        self.mymb_payment_failed_page = self.doc.get('mymb_payment_failed_page')
        #solr section
        self.solr = None
        
        #mysql section
        # self.mysql_settings = self.doc.get('mysql_settings').as_dict()
        # self.mysql_connection = None

    def get_solr_instance(self , isSolrMymbBackoffice = False):
        """Get the Solr instance from the Mymb Settings DocType"""

        if isSolrMymbBackoffice:
            self.solr = Solr(self.solr_mymb_backoffice)
        else:
            self.solr = Solr(self.solr_url)
    
    def get_no_reply_email(self):
        """Get the no-reply email from the document, ensuring it doesn't raise an error if the field is missing."""
        return getattr(self.doc, 'no_reply_email_b2b', None)  # Returns None if field doesn't exist

    def get_api_drupal(self):
        """Get the Solr image instance from the Mymb Settings DocType"""
        api_drupal = self.doc.get('api_drupal')
        return api_drupal
    
    def get_image_uri_instance(self):
        """Get the Solr image instance from the Mymb Settings DocType"""
        return self.image_uri
    
    def get_mymb_payment_success_page(self):
        """Get Success payment page from the Mymb Settings DocType"""

        return self.mymb_payment_success_page
    
    def get_mymb_payment_failed_page(self):
        """Get Success payment page from the Mymb Settings DocType"""

        return self.mymb_payment_failed_page
    
    def get_email_b2b(self):
        """Get the email b2b support instance from the Mymb  Settings DocType"""
        email_b2b = self.doc.get('email_b2b')
        return email_b2b
    
    def get_mymb_api_house(self):
        """Get the email b2b support instance from the Mymb  Settings DocType"""
        mymb_api_house = self.doc.get('mymb_api_house')
        return mymb_api_house

    def get_mysql_connection(self):
        """Get the MySQL connection from the Mymb Settings DocType"""
        if not hasattr(self, 'mysql_connection'):
            username = self.doc.get('db_username')
            db_password = get_decrypted_password("Mymb Settings", self.doc.name, 'db_password')  # Decrypt the password
            db_host = self.doc.get('db_host')
            db_port = self.doc.get('db_port')
            db_mymb_item = self.doc.get('db_item_data')


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
    
    def get_mysql_connection_b2b(self , is_data_property=True, is_db_transaction=False , is_erp_db=False):
        """
        Get the MySQL connection from the Mymb Settings DocType with circuit breaker protection.
        Uses conservative connection pool limits to prevent one tenant from blocking others.
        """
        if not hasattr(self, 'mysql_connection'):
            username = self.doc.get('db_username')
            db_password = get_decrypted_password("Mymb Settings", self.doc.name, 'db_password')  # Decrypt the password
            db_host = self.doc.get('db_host')
            db_port = self.doc.get('db_port')
            if is_db_transaction:
                db_name = self.doc.get('db_transactions')
            elif is_erp_db:
                db_name = self.doc.get('db_erp')
            elif is_data_property:
                db_name = self.doc.get('db_item_data')

            # Get current site name for logging
            current_site = getattr(frappe.local, 'site', 'unknown')

            db_config = {
                'drivername': 'mysql',
                'username': username,
                'password': db_password,
                'host': db_host,
                'port': db_port,
                'database': db_name
            }

            # Create circuit breaker for this DB connection
            db_circuit_breaker = CircuitBreaker(
                name=f"b2b_db_{db_host}_{db_name}_{current_site}",
                failure_threshold=3,
                timeout_seconds=60,
                half_open_max_calls=2
            )

            # Wrap DB connection creation with circuit breaker
            def _create_db_connection():
                return Database(
                    db_config,
                    pool_size=self.DEFAULT_POOL_SIZE,
                    max_overflow=self.DEFAULT_MAX_OVERFLOW
                )

            try:
                self.mysql_connection = db_circuit_breaker.call(_create_db_connection)
            except Exception as e:
                frappe.log_error(
                    message=f"Failed to create B2B DB connection for {current_site}: {str(e)}",
                    title="B2B DB Connection Failed"
                )
                raise

        return self.mysql_connection