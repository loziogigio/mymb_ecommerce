from sqlalchemy import create_engine, Column, String, Integer, Float, DateTime, text
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class TmpCarrello(Base):
    __tablename__ = 'tmp_carrello'  

    id_cliente = Column(String(50), primary_key=True)
    id_carrello = Column(Integer, primary_key=True)
    address_code = Column(String(10), primary_key=True)
    nota = Column(String, nullable=True)  
    listino_code = Column(String(10), nullable=True)
    listino_type = Column(String(10), nullable=True)
    data_consegna = Column(DateTime, nullable=False)
    stato = Column(String(5), nullable=False, default='A')
    data_registrazione = Column(DateTime, nullable=True)
    spese_trasporto = Column(Float, nullable=False, default=0)
    totale_netto = Column(Float, nullable=False, default=0)
    totale_lordo = Column(Float, nullable=False, default=0)
    totale_iva = Column(Float, nullable=False, default=0)
    totale_doc = Column(Float, nullable=False, default=0)
    codice_giro_consegna = Column(String(10), nullable=False, default='0')
    codice_punto_vendita = Column(String(10), nullable=False, default='0')
    gold_doc_name = Column(String(100), nullable=True)
    orario_consegna = Column(String(50), nullable=True)
    codice_trasporto = Column(String(10), nullable=True)

    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}
    
    def to_b2b_dict(self):
        return {
            "client_id":self.id_cliente,
            "id_cart":self.id_carrello,
            "status":self.stato,
            "totale_net":self.totale_netto,
            "cart_name":self.gold_doc_name,
            "creation_date":self.data_registrazione
        }
