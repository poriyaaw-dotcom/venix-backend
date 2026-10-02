# app/core/dependencies.py
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Optional
from jose import jwt, JWTError

from app.db.session import get_db
from app.models.user import User
from app.core.config import get_settings

security = HTTPBearer(auto_error=False)
settings = get_settings()

class MockVisitorUser:
    """Mock user for when no token is provided."""
    id = None
    phone_number = "visitor"
    customer_group = "visitor"
    is_admin = False

async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
):
    # 1. If no token, return visitor
    if credentials is None:
        return MockVisitorUser()
    
    token = credentials.credentials
    
    # 2. Decode the JWT Token
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        sub: str = payload.get("sub")
        if sub is None:
            raise HTTPException(status_code=401, detail="Invalid token payload")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")

    # 3. Smart Lookup: Try ID first, then Phone Number
    user = None
    
    # Try finding by ID (in case 'sub' is the user ID like "1")
    try:
        user_id = int(sub)
        user = db.query(User).filter(User.id == user_id).first()
    except (ValueError, TypeError):
        pass
        
    # If not found by ID, try finding by phone number
    if not user:
        user = db.query(User).filter(User.phone_number == sub).first()

    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    
    return user

def require_admin(current_user: User = Depends(get_current_user)):
    """Dependency that ensures the current user is an admin."""
    if not getattr(current_user, 'is_admin', False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Admin privileges required"
        )
    return current_user