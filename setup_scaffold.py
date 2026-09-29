import os
from pathlib import Path

BASE_DIR = Path(__file__).parent

DIRS = [
    "app/core", "app/api/v1", "app/models", "app/schemas", 
    "app/services", "app/repositories", "app/integrations", 
    "app/workers", "app/audit", "app/db", "migrations/versions", 
    "tests", "docs"
]

FILES = {
    "requirements.txt": """\
fastapi==0.111.0
uvicorn[standard]==0.30.1
sqlalchemy==2.0.30
alembic==1.13.1
pydantic==2.7.4
pydantic-settings==2.3.3
psycopg2-binary==2.9.9
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
redis==5.0.6
httpx==0.27.0
pytest==8.2.2
pytest-asyncio==0.23.7
""",
    ".env.example": """\
DATABASE_URL=postgresql://venix_user:venix_password@localhost:5432/venix_db
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=your-super-secret-key-change-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
APP_NAME=Venix Shop API
APP_VERSION=1.0.0
DEBUG=True
""",
    "docker-compose.yml": """\
version: '3.8'
services:
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: venix_user
      POSTGRES_PASSWORD: venix_password
      POSTGRES_DB: venix_db
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
volumes:
  postgres_data:
""",
    "Dockerfile": """\
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
""",
    "README.md": """\
# Venix Shop Backend
Run `docker-compose up -d` then `uvicorn app.main:app --reload`
""",
    "app/__init__.py": "",
    "app/core/__init__.py": "",
    "app/api/__init__.py": "",
    "app/api/v1/__init__.py": "",
    "app/models/__init__.py": "",
    "app/schemas/__init__.py": "",
    "app/services/__init__.py": "",
    "app/repositories/__init__.py": "",
    "app/integrations/__init__.py": "",
    "app/workers/__init__.py": "",
    "app/audit/__init__.py": "",
    "app/db/__init__.py": "",
    "tests/__init__.py": "",
    "app/core/config.py": """\
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache

class Settings(BaseSettings):
    APP_NAME: str = "Venix Shop API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    DATABASE_URL: str
    REDIS_URL: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8')

@lru_cache()
def get_settings() -> Settings:
    return Settings()
""",
    "app/db/session.py": """\
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from app.core.config import get_settings

settings = get_settings()
engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class Base(DeclarativeBase):
    pass

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
""",
    "app/main.py": """\
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import get_settings
from app.api.v1.health import router as health_router

settings = get_settings()
app = FastAPI(title=settings.APP_NAME, version=settings.APP_VERSION, docs_url="/docs")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router, prefix="/api/v1", tags=["Health"])

@app.get("/")
async def root():
    return {"message": f"Welcome to {settings.APP_NAME}"}
""",
    "app/api/v1/health.py": """\
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.db.session import get_db

router = APIRouter()

@router.get("/health")
def health_check(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        db_status = "healthy"
    except Exception:
        db_status = "unhealthy"
    return {"status": "ok", "database": db_status, "version": "1.0.0"}
"""
}

def create_scaffold():
    print("🚀 Starting Venix Backend Scaffold Generation...")
    for d in DIRS:
        path = BASE_DIR / d
        path.mkdir(parents=True, exist_ok=True)
        print(f"  📁 Created directory: {d}")
    for file_path, content in FILES.items():
        path = BASE_DIR / file_path
        path.write_text(content, encoding='utf-8')
        print(f"  📄 Created file: {file_path}")
    print("\n✅ Scaffold generation complete!")

if __name__ == "__main__":
    create_scaffold()
