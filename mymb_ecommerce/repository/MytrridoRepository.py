from mymb_ecommerce.model.Mytrrido import Mytrrido, get_mytrrido_full_tablename
from mymb_ecommerce.mymb_b2c.settings.configurations import Configurations
from datetime import datetime, timedelta
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine

class MytrridoRepository:

    def __init__(self, external_db_connection_string=None):
        config = Configurations()
        if external_db_connection_string:
            engine = create_engine(external_db_connection_string)
        else:
            db = config.get_mysql_connection(is_erp_db=True)
            engine = db.engine

        self.Session = sessionmaker(bind=engine)
        self.session = None

    def __enter__(self):
        self.session = self.Session()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.session.close()

    def get_all_records(self, limit=None, page=None, time_laps=None, filters=None):
        with self.Session() as session:
            query = session.query(Mytrrido)
            if time_laps:
                time_threshold = datetime.now() - timedelta(minutes=int(time_laps))
                query = query.filter(Mytrrido.created_at >= time_threshold)

            if filters:
                for key, value in filters.items():
                    if hasattr(Mytrrido, key):
                        column = getattr(Mytrrido, key)
                        if isinstance(value, list):
                            query = query.filter(column.in_(value))
                        else:
                            query = query.filter(column == value)

            if limit:
                query = query.limit(limit)
                if page and page > 1:
                    query = query.offset((page - 1) * limit)

            return query.all()

    def get_record_by_filters(self, **filters):
        with self.Session() as session:
            query = session.query(Mytrrido)
            for key, value in filters.items():
                if hasattr(Mytrrido, key):
                    column = getattr(Mytrrido, key)
                    query = query.filter(column == value)
            return query.first()
