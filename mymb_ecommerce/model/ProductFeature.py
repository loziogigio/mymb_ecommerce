from sqlalchemy import create_engine, Column, String, Integer, Float, Boolean, DateTime, Text, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

Base = declarative_base()

class ProductFeature(Base):
    __tablename__ = 'product_feature'

    product_code = Column(String(50), primary_key=True)
    feature_id = Column(Integer, primary_key=True)
    datedata = Column(DateTime, nullable=True)
    numericdata = Column(Float, nullable=True)
    stringdata = Column(Text, nullable=True)
    booleandata = Column(Boolean, nullable=True)
    status = Column(Integer, nullable=False)
    user_id = Column(Integer, nullable=False, default=0)
    lastoperation = Column(DateTime, nullable=False, server_default=text('CURRENT_TIMESTAMP'))
    domain_id = Column(Integer, nullable=True)
    linenumber = Column(Integer, nullable=True)
    uom_id = Column(String(8), nullable=False, default="0")
    notmodifiablefromextern = Column(Boolean, nullable=True)

    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}
