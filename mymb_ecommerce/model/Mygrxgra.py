# mymb_ecommerce/mymb_ecommerce/model/MyGrxGra.py

import frappe
from sqlalchemy import Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

def get_mygrxgra_full_tablename():
    db = frappe.get_doc('Mymb Settings').get("db_erp")
    return f"{db}.mygrxgru"

class Mygrxgra(Base):
    __tablename__ = 'mygrxgru'

    csoci = Column(String(4), primary_key=True, nullable=False)
    cgrup_darti = Column(String(24), primary_key=True, nullable=False)
    cgrup_darti_r = Column(String(24), primary_key=True, nullable=False)
    nlive_dpref = Column(Integer, nullable=True)

    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}
