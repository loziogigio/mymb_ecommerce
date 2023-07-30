from sqlalchemy import create_engine, Column, String, Integer, BigInteger, Boolean, DateTime, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

Base = declarative_base()

class Media(Base):
    __tablename__ = 'media'

    media_id = Column(BigInteger, primary_key=True, autoincrement=True)
    entity_id = Column(String(20), nullable=False, index=True)
    entity_code = Column(String(255), nullable=False)
    checksum = Column(String(255), nullable=False)
    mime = Column(String(255), nullable=False)
    filename = Column(String(255), nullable=False)
    filename_orig = Column(String(255), nullable=False)
    path = Column(String, nullable=False)
    sorting = Column(Integer, nullable=False)
    media_area_id = Column(String(20))
    status = Column(Integer, default=0, nullable=False)
    created_date = Column(DateTime, server_default=text('CURRENT_TIMESTAMP'), nullable=False)
    user_id = Column(Integer, default=0, nullable=False)
    lastoperation = Column(DateTime, server_default=text('CURRENT_TIMESTAMP'), nullable=False)

    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}