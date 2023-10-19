import frappe
from sqlalchemy import create_engine, Column, String, Integer, Boolean, DateTime, text, ForeignKey
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

def get_channel_product_full_tablename():
    db = frappe.get_doc('Mymb b2c Settings').get("db_item_data")
    return f"{db}.channel_product"


class ChannellProduct(Base):


    __tablename__ = 'channel_product'

    channel_id = Column(String(20), primary_key=True)
    product_code = Column(String(50), primary_key=True)
    product_ref = Column(String(50), nullable=False)
    confirmed = Column(Boolean, nullable=False, default=False)
    insert_date = Column(DateTime, nullable=False)
    validation_date = Column(DateTime, nullable=True)
    user_id = Column(Integer, nullable=True, default=0)
    lastoperation = Column(DateTime, server_default=text('CURRENT_TIMESTAMP'), nullable=False)
    forcedtoinclude = Column(Boolean, nullable=True)

    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}
