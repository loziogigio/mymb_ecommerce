from mymb_ecommerce.model.Mygrxgra import Mygrxgra
from mymb_ecommerce.model.Mygruart import Mygruart
from mymb_ecommerce.repository.B2BBaseRepository import B2BBaseRepository

class MygrxgraRepository(B2BBaseRepository):
    def __init__(self, is_erp_db=True):
        super().__init__(is_erp_db=is_erp_db)

    def get_all_records(self, limit=None, page=None, filters=None, to_dict=False):
        query = self.session.query(Mygrxgra, Mygruart).join(
            Mygruart, Mygrxgra.cgrup_darti == Mygruart.cgrup_darti
        )

        # Apply filters on Mygrxgra
        if filters is not None:
            for key, value in filters.items():
                if hasattr(Mygrxgra, key):
                    if isinstance(value, list):
                        query = query.filter(getattr(Mygrxgra, key).in_(value))
                    else:
                        query = query.filter(getattr(Mygrxgra, key) == value)

        # Pagination
        if limit is not None:
            query = query.limit(limit)
            if page is not None and page > 1:
                query = query.offset((page - 1) * limit)

        results = query.all()

        if to_dict:
            return [
                {
                    **record[0].to_dict(),            # Mygrxgra fields
                    "tgrup_darti": record[1].tgrup_darti  # Add specific field from Mygruart
                } for record in results
            ]
        else:
            return results
