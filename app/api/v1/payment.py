from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone

from app.db.session import get_db
from app.models.bank_info import BankInfo
from app.models.order import Order
from app.models.user import User
from app.core.dependencies import get_current_user, require_admin

router = APIRouter(prefix="/payment", tags=["Payment"])

# --- Schemas ---
class BankInfoResponse(BaseModel):
    bank_name: str
    account_holder_name: str
    card_number: str
    sheba_number: str
    class Config:
        from_attributes = True

class BankInfoUpdateSchema(BaseModel):
    bank_name: str
    account_holder_name: str
    card_number: str
    sheba_number: str

class TrackingNumberSchema(BaseModel):
    order_id: int
    tracking_number: str

# --- Public Endpoints ---
@router.get("/bank-info", response_model=BankInfoResponse)
def get_public_bank_info(db: Session = Depends(get_db)):
    # Get the first active bank info
    info = db.query(BankInfo).filter(BankInfo.is_active == True).first()
    if not info:
        # Fallback if admin hasn't set it up yet
        return BankInfoResponse(
            bank_name="بانک قرض الحسنه رسالت",
            account_holder_name="سید امیرعلی موسوی",
            card_number="5041721246057450",
            sheba_number="IR790700010001113795841001"
        )
    return info

@router.post("/submit-tracking")
def submit_tracking_number(
    data: TrackingNumberSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    order = db.query(Order).filter(Order.id == data.order_id, Order.user_id == current_user.id).first()
    if not order:
        raise HTTPException(status_code=404, detail="سفارش یافت نشد")
    
    order.bank_tracking_number = data.tracking_number
    order.paid_at = datetime.now(timezone.utc)
    # Note: We keep status as 'pending_payment' until admin verifies it, 
    # or you can change it to 'paid' immediately. Let's keep it pending for admin verification.
    
    db.commit()
    return {"message": "شماره پیگیری با موفقیت ثبت شد. منتظر تایید مدیریت باشید."}

# --- Admin Endpoints ---
@router.get("/admin/bank-info")
def get_admin_bank_info(db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    info = db.query(BankInfo).filter(BankInfo.is_active == True).first()
    if not info:
        return None
    return {
        "id": info.id,
        "bank_name": info.bank_name,
        "account_holder_name": info.account_holder_name,
        "card_number": info.card_number,
        "sheba_number": info.sheba_number
    }

@router.post("/admin/bank-info")
def update_bank_info(
    data: BankInfoUpdateSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    # Deactivate all old ones
    db.query(BankInfo).update({"is_active": False})
    
    # Create new one
    new_info = BankInfo(
        bank_name=data.bank_name,
        account_holder_name=data.account_holder_name,
        card_number=data.card_number,
        sheba_number=data.sheba_number,
        is_active=True
    )
    db.add(new_info)
    db.commit()
    db.refresh(new_info)
    
    return {"message": "اطلاعات بانکی با موفقیت بروزرسانی شد"}
