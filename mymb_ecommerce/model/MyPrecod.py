# mymb_ecommerce/mymb_ecommerce/model/MyPrecod.py
import frappe
from sqlalchemy import Column, Integer, String, DateTime, DECIMAL
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

def get_myprecod_full_tablename():
    db = frappe.get_doc('Mymb b2c Settings').get("db_erp")
    return f"{db}.myprecod"

class MyPrecod(Base):
    __tablename__ = 'myprecod'

    csoci = Column(String(4), primary_key=True, nullable=False)
    cprec_darti = Column(String(24), primary_key=True, nullable=False)
    iprec_darti = Column(DateTime, primary_key=True, nullable=False)
    bdele = Column(String(1), nullable=False, default='S')
    tprec_darti = Column(String(50), nullable=True)
    cgrup_darti = Column(String(24), nullable=True)
    psovr_sscor = Column(DECIMAL(6,3), nullable=True)
    calle = Column(Integer, nullable=True, default=0)
    cdivi = Column(String(4), nullable=True, default='0')

    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}
