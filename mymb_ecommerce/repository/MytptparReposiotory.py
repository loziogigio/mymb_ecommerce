# mymb_ecommerce/mymb_ecommerce/repository/MytptparRepository.py

from mymb_ecommerce.model.Mytptpar import Mytptpar
from mymb_ecommerce.model.Mytparti import Mytparti

from mymb_ecommerce.model.Myartmag import Myartmag
from mymb_ecommerce.repository.B2BBaseRepository import B2BBaseRepository
# mymb_ecommerce/mymb_ecommerce/repository/MytptparRepository.py
from sqlalchemy import func

class MytptparRepository(B2BBaseRepository):
    def __init__(self, is_erp_db=True):
        super().__init__(is_erp_db=is_erp_db)

    def get_all_records(self, limit=10, page=None, filters=None, to_dict=False):
        query = self.session.query(Mytptpar)

        # Apply filters
        if filters is not None:
            for key, value in filters.items():
                if hasattr(Mytptpar, key):
                    if isinstance(value, list):
                        # If the value is a list, use the IN statement
                        query = query.filter(getattr(Mytptpar, key).in_(value))
                    else:
                        # Else, use the equality filter
                        query = query.filter(getattr(Mytptpar, key) == value)

        # Apply limit and offset for pagination
        if limit is not None:
            query = query.limit(limit)
            if page is not None and page > 1:
                query = query.offset((page - 1) * limit)

        results = query.all()

        if to_dict:
            return [record.to_dict() for record in results]
        else:
            return [record.__dict__ for record in results]
    def get_id_subtype(self, ctipo_dtpar='0', to_dict=False):
        # Define the subquery for tp
        tp_subquery = self.session.query(
            Myartmag.ctipo_darti,
            func.count(Myartmag.oarti).label('tot_prod')
        ).filter(
            Myartmag.binse_inocl == 'S'
        ).group_by(
            Myartmag.ctipo_darti
        ).subquery()

        # Main query
        query = self.session.query(
            Mytparti.ctipo_dtpar,
            Mytptpar.ttipo_dtpar,
            Mytparti.ctipo_darti,
            Mytparti.ttipo_darti,
            tp_subquery.c.tot_prod
        ).join(
            Mytptpar, Mytparti.ctipo_dtpar == Mytptpar.ctipo_dtpar
        ).join(
            tp_subquery, Mytparti.ctipo_darti == tp_subquery.c.ctipo_darti
        ).filter(
            # 'cats_no_show.cat_id IS NULL',
            Mytparti.ctipo_dtpar == ctipo_dtpar,
            tp_subquery.c.tot_prod > 0
        ).order_by(
            Mytparti.ctipo_dtpar, Mytparti.ttipo_darti
        )

        results = query.all()

        if to_dict:
            return [result._asdict() for result in results]
        else:
            return results


