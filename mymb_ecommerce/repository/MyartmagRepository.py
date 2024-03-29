# mymb_ecommerce/mymb_ecommerce/repository/MyartmagRepository.py

from mymb_ecommerce.model.Myartmag import Myartmag
from mymb_ecommerce.settings.configurations import Configurations
from sqlalchemy import create_engine, and_
from sqlalchemy.orm import sessionmaker
from sqlalchemy import desc
from datetime import datetime, timedelta


class MyartmagRepository:

    def __init__(self, external_db_connection_string=None):
        # Get the Configurations instance
        config = Configurations()

        # If an external DB connection string is provided, use it. Otherwise, use the default connection
        if external_db_connection_string:
            engine = create_engine(external_db_connection_string)
        else:
            db = config.get_mysql_connection()
            engine = db.engine

        Session = sessionmaker(bind=engine)
        self.session = Session()

    def __del__(self):
        self.session.close()

    def get_all_records(self, limit=None, page=None, time_laps=None, to_dict=False, filters=None):
        query = self.session.query(Myartmag)

        if time_laps is not None:
            time_laps = int(time_laps)
            time_threshold = datetime.now() - timedelta(minutes=time_laps)
            query = query.filter(Myartmag.created_at >= time_threshold)

        # Apply the filters
        if filters is not None:
            for key, value in filters.items():
                # Make sure the attribute exists in the Myartmag model
                if hasattr(Myartmag, key):
                    query = query.filter(getattr(Myartmag, key) == value)

        # Order by dinse_ianag in descending order
        query = query.order_by(desc(Myartmag.dinse_ianag))
        
        # Apply limit and offset for pagination
        if limit is not None:
            query = query.limit(limit)
            if page is not None and page > 1:
                query = query.offset((page - 1) * limit)

        results = query.all()

        if to_dict:
            return [myartmag.to_dict() for myartmag in results]
        else:
            return results
