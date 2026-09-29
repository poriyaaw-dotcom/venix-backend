# app/services/auth_service.py
import random
from datetime import datetime, timedelta
from jose import jwt
from sqlalchemy.orm import Session
import redis

from app.models.user import User
from app.models.enums import CustomerGroup
from app.core.config import get_settings

settings = get_settings()
# Connect to Redis (using the URL from .env)
redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)

def generate_otp() -> str:
    """Generates a secure 6-digit OTP."""
    return f"{random.randint(100000, 999999)}"

def request_otp(phone_number: str) -> str:
    """Generates OTP, stores it in Redis with a 2-minute expiration, and returns it."""
    otp = generate_otp()
    redis_key = f"otp:{phone_number}"
    
    # Store OTP in Redis for 120 seconds
    redis_client.setex(redis_key, 120, otp)
    
    # TODO: Integrate SMS Provider here later
    print(f"🔥 [MOCK SMS] Your OTP for {phone_number} is: {otp}")
    
    return otp

def verify_otp_and_login(db: Session, phone_number: str, otp_code: str) -> dict:
    """Verifies OTP, creates/updates user, and returns a JWT token."""
    redis_key = f"otp:{phone_number}"
    stored_otp = redis_client.get(redis_key)
    
    if not stored_otp or stored_otp != otp_code:
        raise ValueError("Invalid or expired OTP code")
    
    # OTP is valid, delete it from Redis so it can't be reused
    redis_client.delete(redis_key)
    
    # Find or create user
    user = db.query(User).filter(User.phone_number == phone_number).first()
    if not user:
        user = User(phone_number=phone_number, customer_group=CustomerGroup.VISITOR)
        db.add(user)
        db.commit()
        db.refresh(user)
    
    # Generate JWT Token
    expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode = {"sub": str(user.id), "exp": expire}
    token = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    
    return {
        "access_token": token,
        "token_type": "bearer",
        "customer_group": user.customer_group.value
    }