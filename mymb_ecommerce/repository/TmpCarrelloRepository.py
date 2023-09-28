# mymb_ecommerce/mymb_ecommerce/repository/TmpCarrelloRepository.py

from mymb_ecommerce.model.TmpCarrello import TmpCarrello
from mymb_ecommerce.repository.B2BBaseRepository import B2BBaseRepository
from datetime import datetime, timedelta
from sqlalchemy import desc

class TmpCarrelloRepository(B2BBaseRepository):

    def get_all_records(self, limit=None, page=None, time_laps=None, to_dict=False, filters=None, sort_by=None, sort_order='asc'):
        query = self.session.query(TmpCarrello)

        if time_laps is not None:
            time_laps = int(time_laps)
            time_threshold = datetime.now() - timedelta(minutes=time_laps)
            query = query.filter(TmpCarrello.data_registrazione >= time_threshold)

        # Apply the filters
        if filters is not None:
            for key, value in filters.items():
                if hasattr(TmpCarrello, key):
                    query = query.filter(getattr(TmpCarrello, key) == value)

        # Order by specified attribute in specified order
        if sort_by and hasattr(TmpCarrello, sort_by):
            if sort_order == 'desc':
                query = query.order_by(desc(getattr(TmpCarrello, sort_by)))
            else:
                query = query.order_by(getattr(TmpCarrello, sort_by))
        else:
            # Default ordering if none specified
            query = query.order_by(desc(TmpCarrello.data_registrazione))

        # Apply limit and offset for pagination
        if limit is not None:
            query = query.limit(limit)
            if page is not None and page > 1:
                query = query.offset((page - 1) * limit)

        results = query.all()

        if to_dict:
            return [tmp_carrello.to_dict() for tmp_carrello in results]
        else:
            return results
