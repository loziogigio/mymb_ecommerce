from sqlalchemy import Column, Integer, String, DateTime, Float
from sqlalchemy.ext.declarative import declarative_base
Base = declarative_base()

class Order(Base):
    __tablename__ = 'orders'

    order_id = Column(Integer, primary_key=True)
    external_ref = Column(String)
    uid = Column(String)
    email = Column(String)
    payment_method = Column(String)
    status = Column(String)
    currency = Column(String)
    total_amount = Column(Float)
    creation_date = Column(DateTime)
    modify_date = Column(DateTime)
    billing_profile_id = Column(Integer)
    billing_country = Column(String)
    billing_prov = Column(String)
    billing_city = Column(String)
    billing_address = Column(String)
    billing_postalcode = Column(String)
    billing_phone = Column(String)
    billing_name = Column(String)
    billing_company = Column(String)
    billing_vat = Column(String)
    billing_pec = Column(String)
    billing_sdi = Column(String)
    invoice_required = Column(Integer)
    private_invoice = Column(Integer)
    codfisc = Column(String)
    shipping_profile_id = Column(Integer)
    shipping_country = Column(String)
    shipping_prov = Column(String)
    shipping_city = Column(String)
    shipping_address = Column(String)
    shipping_postalcode = Column(String)
    shipping_phone = Column(String)
    shipping_name = Column(String)
    channel_id = Column(Integer)
    # bdeli = Column(Float)
    # berro_ddeli = Column(Float)
    terro_ddeli = Column(String)
    # dprim_ddeli = Column(Float)
    # dulti_ddeli = Column(Float)
    # nnume_ddeli = Column(Integer)
    # oelen_dbmsx = Column(String)
    # bproc = Column(Float)
    # berro_dproc = Column(Float)
    # terro_dproc = Column(Float)
    # dprim_dproc = Column(Float)
    # dulti_dproc = Column(Float)
    # nnume_dproc = Column(Integer)
    # ccaus_sdocu_g = Column(String)
    # ycale_dgest = Column(Integer)
    # nprot_ddocu_g = Column(String)
    # mail_sent = Column(Integer)
    # active = Column(Integer)
    # link_vett = Column(String)
    # date_link_vett = Column(DateTime)
    # mail_link_vett_sent = Column(Integer)
    # receipt_mail_sent = Column(Integer)

    def to_json(self):
        return {
            'order_id': self.order_id,
            'external_ref': self.external_ref,
            'uid': self.uid,
            'email': self.email,
            'payment_method': self.payment_method,
            'status': self.status,
            'currency': self.currency,
            'total_amount': self.total_amount,
            'creation_date': self.creation_date.strftime('%Y-%m-%d %H:%M:%S') if self.creation_date else None,
            'modify_date': self.modify_date.strftime('%Y-%m-%d %H:%M:%S') if self.modify_date else None,
            # 'billing_profile_id': self.billing_profile_id,
            # 'billing_country': self.billing_country,
            # 'billing_prov': self.billing_prov,
            # 'billing_city': self.billing_city,
            # 'billing_address': self.billing_address,
            # 'billing_postalcode': self.billing_postalcode,
            # 'billing_phone': self.billing_phone,
            # 'billing_name': self.billing_name,
            # 'billing_company': self.billing_company,
            # 'billing_vat': self.billing_vat,
            # 'billing_pec': self.billing_pec,
            # 'billing_sdi': self.billing_sdi,
            # 'invoice_required': self.invoice_required,
            # 'private_invoice': self.private_invoice,
            # 'codfisc': self.codfisc,
            # 'shipping_profile_id': self.shipping_profile_id,
            # 'shipping_country': self.shipping_country,
            # 'shipping_prov': self.shipping_prov,
            # 'shipping_city': self.shipping_city,
            # 'shipping_address': self.shipping_address,
            # 'shipping_postalcode': self.shipping_postalcode,
            # 'shipping_phone': self.shipping_phone,
            # 'shipping_name': self.shipping_name,
            # 'channel_id': self.channel_id,
            # 'bdeli': self.bdeli,
            # 'berro_ddeli': self.berro_ddeli,
            'terro_ddeli': self.terro_ddeli,
            # 'dprim_ddeli': self.dprim_ddeli,
            # 'dulti_ddeli': self.dulti_ddeli,
            # 'nnume_ddeli': self.nnume_ddeli,
            # 'oelen_dbmsx': self.oelen_dbmsx,
            # 'bproc': self.bproc,
            # 'berro_dproc': self.berro_dproc,
            # 'terro_dproc': self.terro_dproc,
            # 'dprim_dproc': self.dprim_dproc,
            # 'dulti_dproc': self.dulti_dproc,
            # 'nnume_dproc': self.nnume_dproc,
            # 'ccaus_sdocu_g': self.ccaus_sdocu_g,
            # 'ycale_dgest': self.ycale_dgest,
            # 'nprot_ddocu_g': self.nprot_ddocu_g,
            # 'mail_sent': self.mail_sent,
            # 'active': self.active,
            # 'link_vett': self.link_vett,
            # 'date_link_vett': self.date_link_vett.strftime('%Y-%m-%d %H:%M:%S') if self.date_link_vett else None,
            # 'mail_link_vett_sent': self.mail_link_vett_sent,
            # 'receipt_mail_sent': self.receipt_mail_sent
        }

