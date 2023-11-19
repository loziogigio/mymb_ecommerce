# mymb_ecommerce/mymb_ecommerce/repository/MyPrecodRepository.py

from mymb_ecommerce.model.MyPrecod import MyPrecod
from mymb_ecommerce.repository.B2BBaseRepository import B2BBaseRepository

class MyPrecodRepository(B2BBaseRepository):

    def get_all_records(self, limit=None, page=None, filters=None, to_dict=False):
        query = self.session.query(MyPrecod)

        # Apply filters
        if filters is not None:
            for key, value in filters.items():
                if hasattr(MyPrecod, key):
                    if isinstance(value, list):
                        query = query.filter(getattr(MyPrecod, key).in_(value))
                    else:
                        query = query.filter(getattr(MyPrecod, key) == value)

        # Add order by clause if needed

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
