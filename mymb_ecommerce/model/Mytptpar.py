# mymb_ecommerce/mymb_ecommerce/model/MyTptpar.py
import frappe
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

def get_mytptpar_full_tablename():
    db = frappe.get_doc('Mymb b2c Settings').get("db_erp")
    return f"{db}.mytptpar"

class Mytptpar(Base):
    __tablename__ = 'mytptpar'

    csoci = Column(String(4), primary_key=True, nullable=False)
    ctipo_dtpar = Column(String(24), primary_key=True, nullable=False)
    itipo_dtpar = Column(DateTime, primary_key=True, nullable=False, default='2000-01-01 00:00:00')
    bdele = Column(String(1), nullable=False, default='S')
    ttipo_dtpar = Column(String(50), nullable=True)
    calle = Column(Integer, nullable=True, default=0)
    cdivi = Column(String(4), nullable=True, default='0')

    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}
