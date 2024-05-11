# mymb_ecommerce/mymb_ecommerce/model/MyTptpar.py
import frappe
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

def get_mytparti_full_tablename():
    db = frappe.get_doc('Mymb b2c Settings').get("db_erp")
    return f"{db}.mytparti"

class Mytparti(Base):
    __tablename__ = 'mytparti'

    csoci = Column(String(4), primary_key=True, nullable=False)
    ctipo_darti = Column(String(24), primary_key=True, nullable=False)
    itipo_darti = Column(DateTime, primary_key=True, nullable=False, default='2000-01-01 00:00:00')
    bdele = Column(String(1), nullable=False, default='S')
    ttipo_darti = Column(String(50), nullable=True)
    oarti_sprot = Column(String(50), nullable=True)
    npoin_nderi_c = Column(Integer, nullable=True)
    bderi_dpref_c = Column(String(1), nullable=False, default='N')
    nchrt_ncoda_p = Column(Integer, nullable=True)
    tpref_ncoda = Column(String(24), nullable=True)
    npori_ncoda_p = Column(Integer, nullable=True)
    npoin_nderi_d = Column(Integer, nullable=True)
    bderi_dpref_d = Column(String(1), nullable=False, default='N')
    nchrt_ndesa_p = Column(Integer, nullable=True)
    tpref_ndesa = Column(String(50), nullable=True)
    npori_ndesa_p = Column(Integer, nullable=True)
    nchrt_ncoda_s = Column(Integer, nullable=True)
    nsuff_ncoda = Column(Integer, nullable=True)
    npori_ncoda_s = Column(Integer, nullable=True)
    bclas_smerc = Column(String(1), nullable=False, default='N')
    bdesc_saggi = Column(String(1), nullable=False, default='N')
    bunmi_salte = Column(String(1), nullable=False, default='N')
    bdati_dstru = Column(String(1), nullable=False, default='N')
    bstru_stecn = Column(String(1), nullable=False, default='N')
    bdati_dgest = Column(String(1), nullable=False, default='N')
    bmaga_sabil = Column(String(1), nullable=False, default='N')
    bforn_sabit = Column(String(1), nullable=False, default='N')
    bclie_sabit = Column(String(1), nullable=False, default='N')
    bterz_sabit = Column(String(1), nullable=False, default='N')
    brepa_sabit = Column(String(1), nullable=False, default='N')
    bimba = Column(String(1), nullable=False, default='N')
    betic = Column(String(1), nullable=False, default='N')
    barti_salte = Column(String(1), nullable=False, default='N')
    bcbar = Column(String(1), nullable=False, default='N')
    calle = Column(Integer, nullable=True, default=0)
    cdivi = Column(String(4), nullable=True, default='0')
    ctipo_dtpar = Column(String(24), nullable=False, default='0')

    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}
