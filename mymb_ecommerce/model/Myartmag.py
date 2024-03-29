from sqlalchemy import Column, BigInteger, String, Float, DateTime, Boolean, Date, Integer
from sqlalchemy.ext.declarative import declarative_base


Base = declarative_base()

class Myartmag(Base):
    __tablename__ = 'myartmag'

    csoci = Column(String(4), primary_key=True, nullable=False)
    oarti = Column(String(40), primary_key=True, nullable=False)
    iarti = Column(DateTime, primary_key=True, nullable=False)
    carti = Column(String(24), nullable=False, index=True)  # MUL indicates indexed
    tarti = Column(String(255), nullable=True)
    cunmi_dmaga = Column(String(8), nullable=True, default='0')
    ndeci_xunmi = Column(Float, nullable=True)  # In SQLAlchemy, Double is named Float
    ccate_sscve = Column(String(24), nullable=False, default='0')
    caiva = Column(String(24), nullable=True)
    bagev_sxiva = Column(String(1), nullable=False, default='N')
    cstat_darti = Column(String(4), nullable=False, default='0')
    qlott_scomm = Column(Float, nullable=True)
    carti_seste = Column(String(24), nullable=True, index=True)
    ccate_sgesa = Column(String(24), nullable=True)
    ccate_scrta = Column(String(4), nullable=False, default='0')
    qscor_sminx = Column(Float, nullable=True)
    barti_seffe = Column(String(1), nullable=False, default='S')
    barti_sprot = Column(String(1), nullable=False, default='N')
    ctipo_darti = Column(String(24), nullable=False, default='0')
    ccate_scpac = Column(String(4), nullable=False, default='0')
    cnume_dcocg_a = Column(String(4), nullable=True, default='0')
    ncocg_dcntr_a = Column(String(40), nullable=True, default='0')
    ccate_scpve = Column(String(4), nullable=False, default='0')
    cnume_dcocg_v = Column(String(4), nullable=True, default='0')
    ncocg_dcntr_v = Column(String(40), nullable=True, default='0')
    ccate_sprov = Column(String(24), nullable=True, default='0')
    ccate_sscac = Column(String(24), nullable=False, default='0')
    odise = Column(String(40), nullable=False, default='0')
    oarti_xrfci = Column(String(40), nullable=False, default='0')
    oarti_xrfdb = Column(String(40), nullable=False, default='0')
    oarti_xrfdp = Column(String(40), nullable=False, default='0')
    oarti_xrife = Column(String(40), nullable=False, default='0')
    ctipo_dcoqu = Column(String(4), nullable=False, default='0')
    cunmi_speso = Column(String(8), nullable=True, default='0')
    qpeso = Column(Float, nullable=True)
    cunmi_svolu = Column(String(8), nullable=True, default='0')
    qvolu = Column(Float, nullable=True)
    tmate = Column(String(50), nullable=True)
    ttrat = Column(String(50), nullable=True)
    tfini = Column(String(50), nullable=True)

    # Continuing the definition in the Item class...

    qpeso_sspec = Column(Float, nullable=True)
    qresa = Column(Float, nullable=True)
    ccate_stoll = Column(String(4), nullable=False, default='0')
    ccate_setic = Column(String(4), nullable=False, default='0')
    oarti_xsost = Column(String(40), nullable=False, default='0')
    dsost_darti = Column(DateTime, nullable=True)
    ccate_sqlta = Column(String(4), nullable=False, default='0')
    ccate_spcta = Column(String(4), nullable=False, default='0')
    ccate_sstoc = Column(String(4), nullable=False, default='0')
    qpunt_drior = Column(Float, nullable=True)
    qscor_smaxx = Column(Float, nullable=True)
    qlott_sminx = Column(Float, nullable=True)
    qlott_smaxx = Column(Float, nullable=True)
    qlott_sstnd = Column(Float, nullable=True)
    qlott_secon = Column(Float, nullable=True)
    qlott_sprod = Column(Float, nullable=True)
    qappr_xlott = Column(Float, nullable=True)
    qgggg_dltim = Column(Float, nullable=True)
    qgggg_danti = Column(Float, nullable=True)
    qgggg_dprea = Column(Float, nullable=True)
    qgggg_daccu = Column(Float, nullable=True)
    ctipo_dmaga = Column(String(4), nullable=False, default='0')
    cmaga = Column(String(24), nullable=False, default='0')
    bmaga_sobbl = Column(String(1), nullable=False, default='N')
    dinse_ianag = Column(DateTime, nullable=True)
    tnoco = Column(String(50), nullable=True)
    ncoef_ssupp = Column(Float, nullable=True)
    ocesp = Column(String(40), nullable=False, default='0')
    basso_acona = Column(String(1), nullable=False, default='N')
    casso_xcona = Column(String(4), nullable=False, default='0')
    qpeso_xcona = Column(Float, nullable=True)
    qsupf_xcona = Column(Float, nullable=True)
    cunmi_sdime = Column(String(8), nullable=True, default='0')

    # Continuing the definition in the Item class...

    qdime_saltz = Column(Float, nullable=True)
    qdime_smaxb = Column(Float, nullable=True)
    qdime_sminb = Column(Float, nullable=True)
    ccate_svama = Column(String(4), nullable=False, default='0')
    ctipo_dlott = Column(String(4), nullable=False, default='0')
    cnume_dlott = Column(String(4), nullable=False, default='0')
    ccate_sstat = Column(String(24), nullable=False, default='0')
    dcamb_sgesa = Column(DateTime, nullable=True)
    ccate_sscac_r = Column(String(24), nullable=False, default='0')
    carti_slung = Column(String(50), nullable=True, index=True)
    tform_dlott_s = Column(String(50), nullable=True)
    tform_dlott_c = Column(String(50), nullable=True)
    tetic_dlott = Column(String(50), nullable=True)
    ctipo_dcdcx = Column(String(8), nullable=False, default='0')
    ccdcx = Column(String(24), nullable=False, default='0')
    bdele = Column(String(1), nullable=False, default='S')
    calle = Column(Integer, nullable=True, default=0)
    cdivi = Column(String(4), nullable=True, default='0')
    tlink = Column(String(4000), nullable=True)
    cprec_darti = Column(String(24), nullable=False, default='0')
    binse_inocl = Column(String(1), nullable=False, default='S')
    besau = Column(String(1), nullable=False, default='N')
    oarti_xgrup = Column(String(40), nullable=False, default='0')
    tpath_dfoto = Column(String(1), nullable=True)
    busat_xcodi = Column(String(1), nullable=False, default='N')
    bnuov = Column(String(1), nullable=False, default='N')
    bstag = Column(String(1), nullable=False, default='N')
    bpren = Column(String(1), nullable=False, default='N')
    bbloc_xcata = Column(String(1), nullable=False, default='N')
    ccata = Column(String(24), nullable=True)
    cnume_dtagl = Column(String(50), nullable=True)
    batti_stagl = Column(String(1), nullable=False, default='N')
    batti_scolo = Column(String(1), nullable=False, default='N')

    # Continuing the definition in the Item class...

    bprom_steor = Column(String(1), nullable=False, default='N')
    barti_srich = Column(String(1), nullable=False, default='N')
    binse_inweb = Column(String(1), nullable=True, default='N')
    tarti_swebx = Column(String(255), nullable=True)
    tarti_xrice = Column(String(4000), nullable=True)
    tarti_seste = Column(String(255), nullable=True)
    busat_xvari = Column(String(1), nullable=False, default='N')
    oarti_xvari_r = Column(String(50), nullable=True)
    nrart_sfigl = Column(Integer, nullable=True)
    nord1 = Column(Integer, nullable=True)
    nord2 = Column(Integer, nullable=True)

    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}




