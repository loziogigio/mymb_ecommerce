# mymb_ecommerce/mymb_ecommerce/repository/OrderRowRepository.py

from mymb_ecommerce.repository.BaseRepository import BaseRepository
from mymb_ecommerce.model.B2COrderRow import B2COrderRow
from datetime import datetime, timedelta

class B2COrderRowRepository(BaseRepository):



    def get_all_records(self, limit=None, page=None, time_laps=None, to_dict=False, filters=None):
        query = self.session.query(B2COrderRow)

        # Apply the filters
        if filters is not None:
            for key, value in filters.items():
                # Make sure the attribute exists in the B2COrderRow model
                if hasattr(B2COrderRow, key):
                    query = query.filter(getattr(B2COrderRow, key) == value)

        # Apply limit and offset for pagination
        if limit is not None:
            query = query.limit(limit)
            if page is not None and page > 1:
                query = query.offset((page - 1) * limit)

        results = query.all()

        if to_dict:
            return [order_row.to_dict() for order_row in results]
        else:
            return results
