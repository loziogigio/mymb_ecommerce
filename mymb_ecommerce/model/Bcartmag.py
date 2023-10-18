# mymb_ecommerce/model/Bcartmag.py
import frappe
from sqlalchemy import create_engine, Column, String, Integer, DateTime, Text, Boolean, CHAR, Float
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


def get_bcartmag_full_tablename():
    db = frappe.get_doc('Mymb b2c Settings').get("db_erp")
    return f"{db}.bcartmag"

class Bcartmag(Base):

    __tablename__ = 'bcartmag'

    csoci = Column(String(4), primary_key=True, nullable=False)
    oarti = Column(String(40), primary_key=True, nullable=False)
    carti = Column(String(24), nullable=False)
    tarti = Column(String(255))
    cunmi_dmaga = Column(String(8), default='0')
    ndeci_xunmi = Column(Float)
    caiva = Column(String(24))
    bagev_sxiva = Column(String(1), nullable=False, default='N')
    cstat_darti = Column(String(4), nullable=False, default='0')
    qlott_scomm = Column(Float)
    carti_seste = Column(String(24))
    ctipo_darti = Column(String(24), nullable=False, default='0')
    ctipo_dtpar = Column(String(24))
    cunmi_speso = Column(String(8), default='0')
    qpeso = Column(Float)
    cunmi_svolu = Column(String(8), default='0')
    qvolu = Column(Float)
    qpeso_sspec = Column(Float)
    oarti_xsost = Column(String(40), default='0')
    dinse_ianag = Column(DateTime)
    cunmi_sdime = Column(String(8), default='0')
    qdime_saltz = Column(Float)
    qdime_smaxb = Column(Float)
    qdime_sminb = Column(Float)
    carti_slung = Column(String(50))
    tlink = Column(String(255))
    cprec_darti = Column(String(24), nullable=False, default='0')
    binse_inocl = Column(String(1), nullable=False, default='S')
    besau = Column(String(1), nullable=False, default='N')
    oarti_xgrup = Column(String(40), nullable=False, default='0')
    tpath_dfoto = Column(CHAR(1))
    bnuov = Column(String(1), nullable=False, default='N')
    bstag = Column(String(1), nullable=False, default='N')
    bpren = Column(String(1), nullable=False, default='N')
    bbloc_xcata = Column(String(1), nullable=False, default='N')
    batti_stagl = Column(String(1), nullable=False, default='N')
    batti_scolo = Column(String(1), nullable=False, default='N')
    bprom_steor = Column(String(1), nullable=False, default='N')
    barti_srich = Column(String(1), nullable=False, default='N')
    carti_swebx = Column(String(255))
    tarti_swebx = Column(String(255))
    ctito_swebx = Column(Text)
    cdesc_swebx = Column(Text)
    cnote_swebx = Column(Text)
    cconf_swebx = Column(String(255))
    quniv_swebx = Column(Float)
    cvalu = Column(String(4))
    aprez_swebx_1 = Column(Float)
    aprez_swebx_2 = Column(Float)
    aprez_swebx_3 = Column(Float)
    aprez_swebx_4 = Column(Float)
    aprez_swebx_5 = Column(Float)
    cbarx_swebx_1 = Column(String(24))
    cbarx_swebx_2 = Column(String(24))
    cbarx_swebx_3 = Column(String(24))
    cbarx_swebx_4 = Column(String(24))
    cbarx_swebx_5 = Column(String(24))
    qdisp = Column(Float)
    kurlx_dfoto_1 = Column(String(255))
    kurlx_dfoto_2 = Column(String(255))
    kurlx_dfoto_3 = Column(String(255))
    kurlx_dfoto_4 = Column(String(255))
    kurlx_dfoto_5 = Column(String(255))
    kurlx_dvide_1 = Column(String(255))
    kurlx_dvide_2 = Column(String(255))
    kurlx_dvide_3 = Column(String(255))
    kurlx_dvide_4 = Column(String(255))
    kurlx_dvide_5 = Column(String(255))
    tnota_salfa_1 = Column(String(255))
    tnota_salfa_2 = Column(String(255))
    tnota_salfa_3 = Column(String(255))
    tnota_salfa_4 = Column(String(255))
    tnota_salfa_5 = Column(String(255))
    tnota_salfa_6 = Column(String(255))
    tnota_salfa_7 = Column(String(255))
    tnota_salfa_8 = Column(String(255))
    tnota_salfa_9 = Column(String(255))
    tnota_salfa_0 = Column(String(255))
    bnota_sflag_1 = Column(String(1))
    bnota_sflag_2 = Column(String(1))
    bnota_sflag_3 = Column(String(1))
    bnota_sflag_4 = Column(String(1))
    bnota_sflag_5 = Column(String(1))
    bnota_sflag_6 = Column(String(1))
    bnota_sflag_7 = Column(String(1))
    bnota_sflag_8 = Column(String(1))
    bnota_sflag_9 = Column(String(1))
    bnota_sflag_0 = Column(String(1))
    qnota_snume_1 = Column(Float)
    qnota_snume_2 = Column(Float)
    qnota_snume_3 = Column(Float)
    qnota_snume_4 = Column(Float)
    qnota_snume_5 = Column(Float)
    qnota_snume_6 = Column(Float)
    qnota_snume_7 = Column(Float)
    qnota_snume_8 = Column(Float)
    qnota_snume_9 = Column(Float)
    qnota_snume_0 = Column(Float)
    bgest_dvari = Column(String(1))
    npara_sctec_1 = Column(Integer)
    tpara_dtpar_1 = Column(String(50))
    btipo_dpara_1 = Column(String(1))
    tpara_sctec_1 = Column(String(50))
    qpara_sctec_1 = Column(Float)
    dpara_sctec_1 = Column(DateTime)
    npara_sctec_2 = Column(Integer)
    tpara_dtpar_2 = Column(String(50))
    btipo_dpara_2 = Column(String(1))
    tpara_sctec_2 = Column(String(50))
    qpara_sctec_2 = Column(Float)
    dpara_sctec_2 = Column(DateTime)
    npara_sctec_3 = Column(Integer)
    tpara_dtpar_3 = Column(String(50))
    btipo_dpara_3 = Column(String(1))
    tpara_sctec_3 = Column(String(50))
    qpara_sctec_3 = Column(Float)
    dpara_sctec_3 = Column(DateTime)
    npara_sctec_4 = Column(Integer)
    tpara_dtpar_4 = Column(String(50))
    btipo_dpara_4 = Column(String(1))
    tpara_sctec_4 = Column(String(50))
    qpara_sctec_4 = Column(Float)
    dpara_sctec_4 = Column(DateTime)
    barti_spadr = Column(String(1), nullable=False, default='N')

    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}