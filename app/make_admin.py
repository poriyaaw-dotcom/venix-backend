# app/make_admin.py
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.session import SessionLocal
from app.models.user import User

def make_admin(phone: str):
    db = SessionLocal()
    user = db.query(User).filter(User.phone_number == phone).first()
    if user:
        user.is_admin = True
        db.commit()
        print(f"✅ User {phone} is now an Admin!")
    else:
        print("❌ User not found.")
    db.close()

if __name__ == "__main__":
    make_admin("09123456789") # Change this if you used a different number