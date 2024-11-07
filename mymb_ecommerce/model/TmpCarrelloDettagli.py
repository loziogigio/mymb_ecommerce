from sqlalchemy import create_engine, Column, String, Integer, Float, DateTime, Boolean, text
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class TmpCarrelloDettagli(Base):
    __tablename__ = 'tmp_carrello_dettagli'

    id_carrello = Column(Integer, primary_key=True)
    oarti = Column(String(100), primary_key=True)
    id_riga = Column(Integer, primary_key=True)
    quantity = Column(Float, nullable=False)
    price = Column(Float, nullable=False)
    price_discount = Column(Float, nullable=False, default=0)
    iva = Column(Float, nullable=False, default=22)
    price_promo = Column(Float, nullable=False, default=0)
    promo = Column(String(100), nullable=False, default='0')
    riga_promo = Column(Integer, nullable=False, default=0)
    sconto1 = Column(String(20), nullable=False, default='0')
    sconto2 = Column(String(20), nullable=False, default='0')
    sconto3 = Column(String(20), nullable=False, default='0')
    sconto4 = Column(String(20), nullable=False, default='0')
    sconto5 = Column(String(20), nullable=False, default='0')
    sconto6 = Column(String(20), nullable=False, default='0')
    date = Column(DateTime, nullable=False)
    qty_min_imballo = Column(Float, nullable=True, default=1)
    um = Column(String(10), nullable=False, default='PZ')
    decimali = Column(Integer, nullable=False, default=2)
    decimali_tot_riga = Column(Integer, nullable=False, default=2)
    omaggio = Column(Boolean, nullable=False, default=False)
    delivery_date = Column(DateTime, nullable=True)

    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}
