from app.api.v1.payment import router as payment_router
from app.models.bank_info import BankInfo
# app/main.py
import os
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
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

# ✅ SECURITY: Disable docs in production to prevent endpoint enumeration
is_prod = os.getenv("ENVIRONMENT") == "production"
docs_url = None if is_prod else "/docs"
redoc_url = None if is_prod else "/redoc"

app = FastAPI(
    title=settings.APP_NAME, 
    version=settings.APP_VERSION, 
    docs_url=docs_url,
    redoc_url=redoc_url
)

# ✅ SECURITY: Strict CORS Configuration
# Only allow the specific frontend URL defined in .env
allowed_origins = [settings.FRONTEND_URL] if getattr(settings, 'FRONTEND_URL', None) else ["http://localhost:5173"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"], # Restrict methods
    allow_headers=["Content-Type", "Authorization", "Accept"], # Restrict headers
)

# ✅ SECURITY: Add Security Headers Middleware
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        # Prevent clickjacking
        response.headers["X-Frame-Options"] = "DENY"
        # Prevent MIME-type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"
        # Enable XSS filtering
        response.headers["X-XSS-Protection"] = "1; mode=block"
        # Enforce HTTPS in production
        if is_prod:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response

app.add_middleware(SecurityHeadersMiddleware)

# ✅ SECURITY: Hide detailed server errors in production
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    if is_prod:
        return JSONResponse(
            status_code=500,
            content={"detail": "یک خطای داخلی در سرور رخ داد. لطفاً دوباره تلاش کنید."}
        )
    # In development, let FastAPI handle it normally to show tracebacks
    raise exc

# Routers
app.include_router(health_router, prefix="/api/v1", tags=["Health"])
app.include_router(auth_router, prefix="/api/v1", tags=["Authentication"])
app.include_router(products_router, prefix="/api/v1", tags=["Products"])
app.include_router(cart_router, prefix="/api/v1", tags=["Cart"])
app.include_router(checkout_router, prefix="/api/v1", tags=["Checkout"])
app.include_router(payments_router, prefix="/api/v1", tags=["Payments"])
app.include_router(reviews_router, prefix="/api/v1", tags=["Reviews"])
app.include_router(favorites_router, prefix="/api/v1", tags=["Favorites"])
app.include_router(admin_router, prefix="/api/v1", tags=["Admin"])
app.include_router(payment_router, prefix="/api/v1", tags=["Payment"])
app.include_router(admin_products_router, prefix="/api/v1", tags=["Admin Products"])

@app.get("/")
async def root():
    return {"message": f"Welcome to {settings.APP_NAME}"}
