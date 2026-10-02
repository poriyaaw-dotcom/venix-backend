# app/main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.admin import router as admin_router
from app.core.config import get_settings

# Routers
from app.api.v1.health import router as health_router
from app.api.v1.auth import router as auth_router
from app.api.v1.products import router as products_router
from app.api.v1.cart import router as cart_router
from app.api.v1.checkout import router as checkout_router
from app.api.v1.payments import router as payments_router
from app.api.v1.reviews import router as reviews_router
from app.api.v1.favorites import router as favorites_router # <-- Added this!

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
app.include_router(auth_router)
app.include_router(products_router)
app.include_router(cart_router)
app.include_router(checkout_router)
app.include_router(payments_router)
app.include_router(reviews_router)
app.include_router(favorites_router) # <-- Added this!
app.include_router(admin_router)

@app.get("/")
async def root():
    return {"message": f"Welcome to {settings.APP_NAME}"}