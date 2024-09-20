from sqlalchemy import create_engine, Column, String, Integer, Text, DateTime, Boolean, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

Base = declarative_base()

class Feature(Base):
    __tablename__ = 'feature'

    feature_id = Column(Integer, primary_key=True, autoincrement=True)
    label = Column(String(100), nullable=False)
    feature_type_id = Column(Integer, nullable=False)
    datatype = Column(String(1), nullable=False)
    description = Column(Text, nullable=True)
    uom_id = Column(String(8), nullable=False, default="0")
    domain_id = Column(Integer, nullable=True)
    status = Column(Integer, nullable=False)
    user_id = Column(Integer, nullable=False, default=0)
    lastoperation = Column(DateTime, nullable=False, server_default=text('CURRENT_TIMESTAMP'))
    external_id = Column(String(100), nullable=True)
    feature_id_derivingfrom = Column(Integer, nullable=True)
    notmodifiablefromextern = Column(Boolean, nullable=True)

    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}
