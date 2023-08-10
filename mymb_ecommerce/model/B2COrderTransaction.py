# mymb_ecommerce/mymb_ecommerce/model/B2COrderTransaction.py

from sqlalchemy import Column, BigInteger, Integer, String, Float, DateTime, Text, LargeBinary
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()

class B2COrderTransaction(Base):
    __tablename__ = 'order_transactions'

    order_id = Column(BigInteger, primary_key=True, nullable=False)
    transaction_id = Column(String(100), primary_key=True, nullable=False)
    transaction_id_drupal = Column(Integer, nullable=True)
    status = Column(String(128), nullable=False, index=True)
    currency = Column(String(10), nullable=False)
    amount = Column(Float, nullable=False)
    remote_id = Column(String(255), nullable=True)
    transaction_date = Column(DateTime, nullable=False, default=func.current_timestamp(), index=True)
    modify_date = Column(DateTime, nullable=True)
    remote_status = Column(String(128), nullable=True)
    message = Column(Text, nullable=True)
    payload = Column(LargeBinary, nullable=True)

    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}
