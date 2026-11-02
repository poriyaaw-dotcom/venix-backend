# create_blogs_table.py
from app.db.session import engine
from app.models.blog import Blog

def create_table():
    try:
        print("⏳ Creating 'blogs' table with all SEO columns...")
        # checkfirst=True ensures it does nothing if the table already exists
        Blog.__table__.create(engine, checkfirst=True)
        print("✅ SUCCESS! 'blogs' table is ready.")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    create_table()