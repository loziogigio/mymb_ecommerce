# mymb_ecommerce/mymb_ecommerce/repository/B2COrderTransactionRepository.py

from mymb_ecommerce.model.B2COrderTransaction import B2COrderTransaction
from mymb_ecommerce.repository.BaseRepository import BaseRepository
from datetime import datetime, timedelta

class B2COrderTransactionRepository(BaseRepository):

    def get_all_records(self, limit=None, page=None, time_laps=None, to_dict=False, filters=None):
        query = self.session.query(B2COrderTransaction)

        if time_laps is not None:
            time_laps = int(time_laps)
            time_threshold = datetime.now() - timedelta(minutes=time_laps)
            query = query.filter(B2COrderTransaction.modify_date >= time_threshold) # Adjust the attribute if needed


        # Apply the filters
        if filters is not None:
            for key, value in filters.items():
                # Make sure the attribute exists in the B2COrderTransaction model
                if hasattr(B2COrderTransaction, key):
                    query = query.filter(getattr(B2COrderTransaction, key) == value)

        # Apply limit and offset for pagination
        if limit is not None:
            query = query.limit(limit)
            if page is not None and page > 1:
                query = query.offset((page - 1) * limit)

        results = query.all()

        if to_dict:
            return [order_transaction.to_dict() for order_transaction in results]
        else:
            return results
