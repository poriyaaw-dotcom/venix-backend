# fix_db.py
from sqlalchemy import create_engine, text
from app.core.config import get_settings

# This grabs your database password and name automatically from your config
settings = get_settings()
engine = create_engine(settings.DATABASE_URL, isolation_level="AUTOCOMMIT")

print("🔧 Connecting to database and fixing ENUMs...")
try:
    with engine.connect() as conn:
        # These commands add the missing options to your database
        conn.execute(text("ALTER TYPE customergroup ADD VALUE IF NOT EXISTS 'NORMAL';"))
        conn.execute(text("ALTER TYPE customergroup ADD VALUE IF NOT EXISTS 'VISITOR';"))
        conn.execute(text("ALTER TYPE customergroup ADD VALUE IF NOT EXISTS 'WHOLESALE';"))
        conn.execute(text("ALTER TYPE customergroup ADD VALUE IF NOT EXISTS 'SHOP_OWNER';"))
    print("✅ Database fixed successfully! You can now log in.")
except Exception as e:
    print(f"❌ Error: {e}")