# mymb_ecommerce/mymb_ecommerce/repository/MyBarcodRepository.py

from mymb_ecommerce.model.MyBarcod import MyBarcod
from mymb_ecommerce.repository.B2BBaseRepository import B2BBaseRepository

class MyBarcodRepository(B2BBaseRepository):

    def get_all_records(self, limit=1, page=None, filters=None, to_dict=False):
        query = self.session.query(MyBarcod)

        # Apply filters
        if filters is not None:
            for key, value in filters.items():
                if hasattr(MyBarcod, key):
                    if isinstance(value, list):
                        # If the value is a list, use the IN statement
                        query = query.filter(getattr(MyBarcod, key).in_(value))
                    else:
                        # Else, use the equality filter
                        query = query.filter(getattr(MyBarcod, key) == value)

         # Add order by clause
        query = query.order_by(MyBarcod.bbarx_sazie.asc())

        # Apply limit and offset for pagination
        if limit is not None:
            query = query.limit(limit)
            if page is not None and page > 1:
                query = query.offset((page - 1) * limit)

        results = query.all()

        if to_dict:
            return [record.to_dict() for record in results]
        else:
            return results
    
