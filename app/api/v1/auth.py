# app/api/v1/auth.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.auth import PhoneRequest, OTPVerifyRequest, TokenResponse
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/request-otp", status_code=200)
def request_otp_endpoint(payload: PhoneRequest):
    """Step 1: User provides phone number, we send (mock) an OTP."""
    # Basic validation for Iranian phone numbers (optional but good practice)
    if not payload.phone_number.startswith("09") or len(payload.phone_number) != 11:
        raise HTTPException(status_code=400, detail="Invalid phone number format. Use 09xxxxxxxxx")
    
    auth_service.request_otp(payload.phone_number)
    return {"message": "OTP sent successfully. Check your terminal (mock SMS)."}

@router.post("/verify-otp", response_model=TokenResponse)
def verify_otp_endpoint(payload: OTPVerifyRequest, db: Session = Depends(get_db)):
    """Step 2: User provides phone number + OTP, we return a JWT token."""
    try:
        result = auth_service.verify_otp_and_login(db, payload.phone_number, payload.otp_code)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))