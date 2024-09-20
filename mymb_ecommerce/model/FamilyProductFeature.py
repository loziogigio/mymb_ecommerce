from sqlalchemy import Column, Integer, String, Text, Float, Boolean, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import text

Base = declarative_base()

class FamilyProductFeature(Base):
    __tablename__ = 'family_product_feature'

    family_id = Column(Integer, primary_key=True, nullable=False)
    feature_id = Column(Integer, primary_key=True, nullable=False)
    linenumber = Column(Integer, nullable=True)
    label = Column(String(100), nullable=True)
    uom_id = Column(String(8), nullable=True, default="0")
    description = Column(Text, nullable=True)
    status = Column(Integer, nullable=False)
    user_id = Column(Integer, nullable=False, default=0)
    lastoperation = Column(DateTime, nullable=False, server_default=text('CURRENT_TIMESTAMP'))
    fromoperator = Column(String(8), nullable=True)
    tooperator = Column(String(8), nullable=True)
    fromnumericvalue = Column(Float, nullable=True)
    tonumericvalue = Column(Float, nullable=True)
    fromdatevalue = Column(DateTime, nullable=True)
    todatevalue = Column(DateTime, nullable=True)
    useinterval = Column(Boolean, nullable=True)
    domain_id = Column(Integer, nullable=True)
    notmodifiablefromextern = Column(Boolean, nullable=True)
    external_id = Column(String(100), nullable=True)

    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}
