# app/main.py
from app.api.v1.cart import router as cart_router
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import get_settings
from app.api.v1.health import router as health_router
from app.api.v1.auth import router as auth_router
from app.api.v1.products import router as products_router # <-- Added this
from app.api.v1.checkout import router as checkout_router

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
app.include_router(products_router) # <-- Added this
app.include_router(cart_router)
app.include_router(checkout_router)

@app.get("/")
async def root():
    return {"message": f"Welcome to {settings.APP_NAME}"}