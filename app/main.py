# app/main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import get_settings

# Routers
from app.api.v1.health import router as health_router
from app.api.v1.auth import router as auth_router
from app.api.v1.products import router as products_router
from app.api.v1.cart import router as cart_router
from app.api.v1.checkout import router as checkout_router
from app.api.v1.payments import router as payments_router
from app.api.v1.reviews import router as reviews_router
from app.api.v1.favorites import router as favorites_router
from app.api.v1.admin import router as admin_router
from app.api.v1.admin_products import router as admin_products_router

settings = get_settings()
app = FastAPI(title=settings.APP_NAME, version=settings.APP_VERSION, docs_url="/docs")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ FIX: Added prefix="/api/v1" to ALL v1 routers so the frontend matches perfectly!
app.include_router(health_router, prefix="/api/v1", tags=["Health"])
app.include_router(auth_router, prefix="/api/v1", tags=["Authentication"])
app.include_router(products_router, prefix="/api/v1", tags=["Products"])
app.include_router(cart_router, prefix="/api/v1", tags=["Cart"])
app.include_router(checkout_router, prefix="/api/v1", tags=["Checkout"])
app.include_router(payments_router, prefix="/api/v1", tags=["Payments"])
app.include_router(reviews_router, prefix="/api/v1", tags=["Reviews"])
app.include_router(favorites_router, prefix="/api/v1", tags=["Favorites"])
app.include_router(admin_router, prefix="/api/v1", tags=["Admin"])
app.include_router(admin_products_router, prefix="/api/v1", tags=["Admin Products"])

@app.get("/")
async def root():
    return {"message": f"Welcome to {settings.APP_NAME}"}