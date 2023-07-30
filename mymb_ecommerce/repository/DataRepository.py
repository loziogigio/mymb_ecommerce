from sqlalchemy import and_, text
from sqlalchemy.orm import sessionmaker
from mymb_ecommerce.mymb_b2c.settings.configurations import Configurations
from mymb_ecommerce.model.Data import Data
class DataRepository:

    def __init__(self):
        # Get the Configurations instance
        config = Configurations()

        # Get the database connection from Configurations class
        db = config.get_mysql_connection()
        engine = db.engine
        Session = sessionmaker(bind=engine)
        self.session = Session()

    def __del__(self):
        self.session.close()

    def get_data_by_entity_codes(self, entity_codes):
        return self.session.query(Data).filter(
            and_(
                Data.entity_code.in_(entity_codes),
                Data.channel_id.in_(["B2C", "DEFAULT"])
            )
        ).order_by(Data.sorting).all()


    def get_data_by_entity_code(self, entity_code, last_operation=None):
        query = self.session.query(Data).filter(
            and_(
                Data.entity_code == entity_code,
                Data.channel_id.in_(["B2C", "DEFAULT"]),
                (Data.lastoperation > last_operation) if last_operation else True
            )
        ).order_by(Data.sorting)
        return query.all()

    def count_data_by_entity_code(self, entity_code, last_operation=None):
        query = self.session.query(Data).filter(
            and_(
                Data.entity_code == entity_code,
                (Data.lastoperation > last_operation) if last_operation else True
            )
        )
        return query.count()

    def get_data_by_entity_code_raw(self, entity_code):
        query = text("SELECT * FROM data WHERE entity_code=:entity_code")
        result = self.session.execute(query, {"entity_code": entity_code}).fetchall()
        return result

    # Add other methods as needed
