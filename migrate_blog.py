# migrate_blog.py
from app.db.session import SessionLocal
from sqlalchemy import text

def run_migration():
    db = SessionLocal()
    try:
        print("⚠️ Dropping the local 'blogs' table to fix permissions...")
        db.execute(text("DROP TABLE IF EXISTS blogs CASCADE"))
        db.commit()
        print("✅ SUCCESS! Table dropped.")
        print("🔄 The table will be automatically recreated with the new SEO columns when you restart the server!")
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    run_migration()