from sqlalchemy import create_engine, Column, String, Integer, Boolean, DateTime, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

Base = declarative_base()

class ChannelFamilyProductFeature(Base):
    __tablename__ = 'channel_family_product_feature'

    channel_id = Column(String(20), primary_key=True)
    family_id = Column(Integer, primary_key=True)
    feature_id = Column(Integer, primary_key=True)
    sorting = Column(Integer, nullable=True)
    usedforsearch = Column(Boolean, nullable=True)
    usedforfacet = Column(Boolean, nullable=True)
    usedfordisplay = Column(Boolean, nullable=True)
    featureidusedinsearch = Column(Boolean, nullable=True)
    usedforvariant = Column(Boolean, nullable=True)
    status = Column(Integer, nullable=False)
    user_id = Column(Integer, nullable=False, default=0)
    lastoperation = Column(DateTime, nullable=False, server_default=text('CURRENT_TIMESTAMP'))

    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}
