from mymb_ecommerce.model.TmpCarrelloDettagli import TmpCarrelloDettagli
from mymb_ecommerce.repository.B2BBaseRepository import B2BBaseRepository
from datetime import datetime, timedelta
from sqlalchemy import desc
import frappe

class TmpCarrelloDettagliRepository(B2BBaseRepository):

    def __init__(self):
        # Initialize the parent class with necessary arguments
        super().__init__(is_data_property=False, is_db_transaction=True, is_erp_db=False, external_db_connection_string=None)

    def get_all_records(self, limit=None, page=None, time_laps=None, to_dict=False, filters=None, sort_by=None, sort_order='asc', id_carrello=None):
        query = self.session.query(TmpCarrelloDettagli)

        # Filter by id_carrello if provided
        if id_carrello is not None:
            query = query.filter(TmpCarrelloDettagli.id_carrello == id_carrello)

        if time_laps is not None:
            time_laps = int(time_laps)
            time_threshold = datetime.now() - timedelta(minutes=time_laps)
            query = query.filter(TmpCarrelloDettagli.date >= time_threshold)

        # Apply additional filters
        if filters is not None:
            for key, value in filters.items():
                if hasattr(TmpCarrelloDettagli, key):
                    query = query.filter(getattr(TmpCarrelloDettagli, key) == value)

        # Order by specified attribute in specified order
        if sort_by and hasattr(TmpCarrelloDettagli, sort_by):
            if sort_order == 'desc':
                query = query.order_by(desc(getattr(TmpCarrelloDettagli, sort_by)))
            else:
                query = query.order_by(getattr(TmpCarrelloDettagli, sort_by))
        else:
            # Default ordering if none specified
            query = query.order_by(desc(TmpCarrelloDettagli.date))

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
        

    def update_delivery_date(self, id_carrello, internal_code, delivery_date):
        """Update the delivery_date of a specific cart row identified by id_carrello and internal_code."""

        try:
            # Convert delivery_date from string to datetime if it's not already a datetime object
            if isinstance(delivery_date, str):
                delivery_date = datetime.strptime(delivery_date, "%d/%m/%Y")

            # Find the cart row by id_carrello and internal_code
            cart_row = self.session.query(TmpCarrelloDettagli).filter(
                TmpCarrelloDettagli.id_carrello == id_carrello,
                TmpCarrelloDettagli.oarti == internal_code
            ).first()

            if cart_row:
                # Update the delivery_date
                cart_row.delivery_date = delivery_date
                self.session.commit()
                return {"status": "success", "message": f"Delivery date updated for cart row with id_carrello {id_carrello} and internal_code {internal_code}"}
            else:
                error_message = f"No cart row found for id_carrello {id_carrello} and internal_code {internal_code}"
                frappe.log_error(message=error_message, title="Update Delivery Date Error")
                return {"status": "error", "message": error_message}

        except Exception as e:
            error_message = f"Error updating delivery date for id_carrello {id_carrello} and internal_code {internal_code}: {str(e)}"
            frappe.log_error(message=error_message, title="Update Delivery Date Exception")
            return {"status": "error", "message": error_message}
