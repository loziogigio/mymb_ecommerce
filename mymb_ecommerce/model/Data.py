from sqlalchemy import create_engine, Column, String, Integer, Float, Boolean, DateTime, desc, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

Base = declarative_base()

class Data(Base):
    __tablename__ = 'data'

    channel_id = Column(String(20), primary_key=True)
    entity_id = Column(String(20), primary_key=True)
    locale_id = Column(String(20), primary_key=True)
    entity_code = Column(String(255), primary_key=True)
    property_id = Column(String(40), primary_key=True)
    sorting = Column(Integer, primary_key=True)
    format = Column(String(50))
    value = Column(String)
    value_num = Column(Float)
    status = Column(Boolean, default=True)
    user_id = Column(Integer, default=0)
    lastoperation = Column(DateTime, server_default=text('CURRENT_TIMESTAMP'))

    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}