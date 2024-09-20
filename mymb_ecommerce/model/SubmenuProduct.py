from sqlalchemy import create_engine, Column, String, Integer, DateTime, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

Base = declarative_base()

class SubmenuProduct(Base):
    __tablename__ = 'submenu_product'

    submenu_id = Column(Integer, primary_key=True)
    product_code = Column(String(50), primary_key=True)
    product_ref = Column(String(50), nullable=False)
    user_id = Column(Integer, nullable=False, default=0)
    lastoperation = Column(DateTime, nullable=False, server_default=text('CURRENT_TIMESTAMP'))

    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}
