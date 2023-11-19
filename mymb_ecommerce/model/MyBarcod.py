# mymb_ecommerce/mymb_ecommerce/model/MyBarcod.py

from sqlalchemy import Column, Integer, String, Date
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class MyBarcod(Base):
    __tablename__ = 'mybarcod'

    csoci = Column(String(4), primary_key=True, nullable=False)
    cbarx = Column(String(24), primary_key=True, nullable=False)
    oarti = Column(String(40), nullable=False)
    bbarx_sazie = Column(String(1), nullable=False, default='N')
    ctipo_dlott = Column(String(4), nullable=False, default='0')
    clott = Column(String(24), nullable=False, default='0')
    calle = Column(Integer, nullable=True, default=0)
    cdivi = Column(String(4), nullable=True, default='0')
    cuser = Column(String(40), nullable=True)
    daggi = Column(Date, nullable=True)
    ccolo = Column(String(8), nullable=False, default='0')
    cfond = Column(String(8), nullable=False, default='0')
    cform = Column(String(8), nullable=False, default='0')
    cimba = Column(String(4), nullable=False, default='0')
    btipo_dsogg = Column(String(1), nullable=False, default='N')
    canag = Column(String(40), nullable=False, default='0')
    ntagl = Column(Integer, nullable=False, default=0)
    ctagl = Column(String(8), nullable=True, default='0')

    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}
