import frappe
from sqlalchemy import create_engine, Column, String, Integer, CHAR, Float
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

def get_mytrrido_full_tablename():
    db = frappe.get_doc('Mymb b2c Settings').get("db_erp")
    return f"{db}.mytrrido"

class Mytrrido(Base):
    __tablename__ = get_mytrrido_full_tablename()

    csoci = Column(String(4), primary_key=True, nullable=False)
    nprog_ielen = Column(Integer, primary_key=True, nullable=False)
    canag_sclie = Column(String(40))
    ccaus_sdocu_1 = Column(String(8))
    ycale_xxxxx_1 = Column(Integer)
    nprot_ddocu_1 = Column(Integer)
    nriga_ddocu_1 = Column(Integer)
    ccaus_sdocu_2 = Column(String(8))
    ycale_xxxxx_2 = Column(Integer)
    nprot_ddocu_2 = Column(Integer)
    nriga_ddocu_2 = Column(Integer)
    ccaus_sdocu_3 = Column(String(8))
    ycale_xxxxx_3 = Column(Integer)
    nprot_ddocu_3 = Column(Integer)
    nriga_ddocu_3 = Column(Integer)
    ccaus_sdocu_4 = Column(String(8))
    ycale_xxxxx_4 = Column(Integer)
    nprot_ddocu_4 = Column(Integer)
    nriga_ddocu_4 = Column(Integer)
    criva = Column(String(8))
    nprot_driva = Column(Integer)
    ycale_driva = Column(Integer)
    oelen_dfatt = Column(Integer)
    nprog_ielen_f = Column(Integer)
    nriga_dfatt = Column(Integer)
    nposi_dfatt = Column(Integer)
