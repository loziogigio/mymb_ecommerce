# mymb_ecommerce/mymb_ecommerce/repository/BaseRepository.py

import frappe
from mymb_ecommerce.settings.configurations import Configurations
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import OperationalError, TimeoutError

class B2BBaseRepository:

    def __init__(self, is_data_property=True, is_db_transaction=False , is_erp_db=False, external_db_connection_string=None):
        try:
            # Get the Configurations instance
            config = Configurations()

            # If an external DB connection string is provided, use it. Otherwise, use the default connection
            if external_db_connection_string:
                engine = create_engine(
                    external_db_connection_string,
                    connect_args={
                        'connect_timeout': 3,
                        'read_timeout': 30,
                        'write_timeout': 30
                    },
                    pool_pre_ping=True,
                    pool_recycle=3600,
                    pool_size=5,
                    max_overflow=10
                )
            else:
                db = config.get_mysql_connection_b2b( is_data_property, is_db_transaction , is_erp_db)
                engine = db.engine

            Session = sessionmaker(bind=engine)
            self.session = Session()
        except (OperationalError, TimeoutError) as db_error:
            # Log the database connection error
            frappe.log_error(
                message=f"B2B Database connection failed: {str(db_error)}",
                title="B2B Database Connection Error"
            )
            # Re-raise to let caller handle it
            raise Exception(f"Failed to connect to B2B database: {str(db_error)}")

    def __del__(self):
        if hasattr(self, 'session') and self.session:
            self.session.close()
