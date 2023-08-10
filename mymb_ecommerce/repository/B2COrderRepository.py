# mymb_ecommerce/mymb_ecommerce/repository/B2COrderRepository.py

from mymb_ecommerce.model.B2COrder import B2COrder
from mymb_ecommerce.repository.BaseRepository import BaseRepository
from datetime import datetime, timedelta
from pydoc import describe

class B2COrderRepository(BaseRepository):


    def get_all_records(self, limit=None, page=None, time_laps=None, to_dict=False, filters=None):
        query = self.session.query(B2COrder)

        if time_laps is not None:
            time_laps = int(time_laps)
            time_threshold = datetime.now() - timedelta(minutes=time_laps)
            query = query.filter(B2COrder.creation_date >= time_threshold) # Adjust the attribute if needed

        # Apply the filters
        if filters is not None:
            for key, value in filters.items():
                # Make sure the attribute exists in the B2COrder model
                if hasattr(B2COrder, key):
                    query = query.filter(getattr(B2COrder, key) == value)

        # Order by desired attribute in descending order (modify as needed)
        query = query.order_by(describe(B2COrder.creation_date)) # Adjust the attribute if needed
        
        # Apply limit and offset for pagination
        if limit is not None:
            query = query.limit(limit)
            if page is not None and page > 1:
                query = query.offset((page - 1) * limit)

        results = query.all()

        if to_dict:
            return [b2c_order.to_dict() for b2c_order in results]
        else:
            return results
