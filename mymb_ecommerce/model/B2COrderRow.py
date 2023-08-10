# mymb_ecommerce/mymb_ecommerce/model/OrderRow.py

from sqlalchemy import Column, BigInteger, Integer, String, Float
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class B2COrderRow(Base):
    __tablename__ = 'order_rows'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    order_id = Column(BigInteger, nullable=False, index=True)
    row_num = Column(Integer, nullable=False)
    row_id = Column(String(100), nullable=False)
    type = Column(String(100), nullable=False)
    sku = Column(String(50), nullable=True, index=True)
    label = Column(String(250), nullable=False)
    quantity = Column(Integer, nullable=False)
    currency = Column(String(10), nullable=False)
    total_amount = Column(Float, nullable=False)
    base_price = Column(Float, nullable=False)
    unit_amount = Column(Float, nullable=False, default=0)

    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}
