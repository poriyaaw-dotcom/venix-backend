# app/core/dependencies.py
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from sqlalchemy.orm import Session
from app.core.config import get_settings
from app.db.session import get_db
from app.models.user import User

settings = get_settings()
security = HTTPBearer(auto_error=False) # auto_error=False allows unauthenticated requests (treated as Visitor)

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    Extracts the JWT token, validates it, and returns the User.
    If no token is provided, returns a default 'Visitor' user object 
    so the API can still calculate Visitor prices.
    """
    if credentials is None:
        # Return a mock visitor user for price calculation if not logged in
        class MockVisitorUser:
            customer_group = "visitor"
            id = None
        return MockVisitorUser()

    try:
        payload = jwt.decode(
            credentials.credentials, 
            settings.SECRET_KEY, 
            algorithms=[settings.ALGORITHM]
        )
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid authentication credentials")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")

    user = db.query(User).filter(User.id == int(user_id)).first()
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    
    return user