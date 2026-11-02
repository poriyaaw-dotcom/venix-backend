from app.db.session import SessionLocal
try:
    from app.models.user import User
except ImportError:
    from app.models.auth import User

db = SessionLocal()
phone = "09019244403"
user = db.query(User).filter(User.phone_number == phone).first()

if user:
    user.is_admin = True
    db.commit()
    print(f"✅ Success! {phone} is now an admin.")
else:
    print(f"❌ User not found. Please log in with {phone} first, then run this again.")
db.close()
