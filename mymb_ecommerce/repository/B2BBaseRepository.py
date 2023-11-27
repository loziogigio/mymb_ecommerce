# mymb_ecommerce/mymb_ecommerce/repository/BaseRepository.py

from mymb_ecommerce.settings.configurations import Configurations
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

class B2BBaseRepository:

    def __init__(self, is_data_property=True, is_db_transaction=False , is_erp_db=False, external_db_connection_string=None):
        # Get the Configurations instance
        config = Configurations()

        # If an external DB connection string is provided, use it. Otherwise, use the default connection
        if external_db_connection_string:
            engine = create_engine(external_db_connection_string)
        else:
            db = config.get_mysql_connection_b2b( is_data_property, is_db_transaction , is_erp_db)
            engine = db.engine

        Session = sessionmaker(bind=engine)
        self.session = Session()

    def __del__(self):
        self.session.close()
