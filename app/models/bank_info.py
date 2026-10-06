from sqlalchemy import Column, Integer, String, Boolean
from app.db.session import Base

class BankInfo(Base):
    __tablename__ = "bank_info"

    id = Column(Integer, primary_key=True, index=True)
    bank_name = Column(String(100), nullable=False)
    account_holder_name = Column(String(100), nullable=False)
    card_number = Column(String(20), nullable=False, unique=True)
    sheba_number = Column(String(30), nullable=False, unique=True)
    is_active = Column(Boolean, default=True)
