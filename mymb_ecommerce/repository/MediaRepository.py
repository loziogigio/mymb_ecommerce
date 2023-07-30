from sqlalchemy import and_, text
from sqlalchemy.orm import sessionmaker
from mymb_ecommerce.mymb_b2c.settings.configurations import Configurations
from mymb_ecommerce.model.Media import Media

class MediaRepository:

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
        return self.session.query(Media).filter(
            and_(
                Media.entity_code.in_(entity_codes)
                # ,Media.channel_id.in_(["B2C", "DEFAULT"])
            )
        ).order_by(Media.sorting).all()

    def get_media_by_entity_code(self, entity_code):
        query = self.session.query(Media).filter(Media.entity_code == entity_code)
        return query.all()

    def get_media_by_entity_id(self, entity_id):
        query = self.session.query(Media).filter(Media.entity_id == entity_id)
        return query.all()
        return result

    # Add other methods as needed
