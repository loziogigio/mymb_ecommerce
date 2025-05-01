# mymb_ecommerce/mymb_ecommerce/model/GroupDarti.py

import frappe
from sqlalchemy import Column, String
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

def get_mygruart_full_tablename():
    db = frappe.get_doc('Mymb Settings').get("db_erp")
    return f"{db}.mygruart"

class Mygruart(Base):
    __tablename__ = 'mygruart'  # Adjust if the actual table name differs

    cgrup_darti = Column(String(24), primary_key=True, nullable=False)
    tgrup_darti = Column(String(255), nullable=True)

    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}
