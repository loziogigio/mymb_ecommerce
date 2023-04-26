from sqlalchemy import create_engine, Column, String, Integer, Float, Boolean, DateTime, desc
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
        return {
            'channel_id': self.channel_id,
            'entity_id': self.entity_id,
            'locale_id': self.locale_id,
            'entity_code': self.entity_code,
            'property_id': self.property_id,
            'sorting': self.sorting,
            'format': self.format,
            'value': self.value,
            'value_num': self.value_num,
            'status': self.status,
            'user_id': self.user_id,
            'lastoperation': self.lastoperation
        }
