import sys
import os

# This ensures Python can find your 'app' folder no matter where you run it from
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.session import engine
from sqlalchemy import text

print("🔧 Fixing missing database columns...")

with engine.begin() as conn:
    # Force add sold_count to products
    conn.execute(text("ALTER TABLE products ADD COLUMN IF NOT EXISTS sold_count INTEGER DEFAULT 0;"))
    
    # Force add is_admin to users
    conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS is_admin BOOLEAN DEFAULT FALSE;"))

print("✅ Database fixed successfully! You can now delete this file.")