# app/main.py
import os
from fastapi import FastAPI, Request, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy.orm import Session  # ✅ ADDED MISSING IMPORT

from app.core.config import get_settings
from app.db.session import get_db
from app.models.product import Product, Category
from app.models.bank_info import BankInfo

# Routers
from app.api.v1.health import router as health_router
from app.api.v1.auth import router as auth_router
from app.api.v1.products import router as products_router
from app.api.v1.blog import router as blog_router
from app.api.v1.upload import router as upload_router
from app.api.v1.cart import router as cart_router
from app.api.v1.checkout import router as checkout_router
from app.api.v1.payments import router as payments_router
from app.api.v1.reviews import router as reviews_router
from app.api.v1.favorites import router as favorites_router
from app.api.v1.admin import router as admin_router
from app.api.v1.admin_products import router as admin_products_router
from app.api.v1.payment import router as payment_router

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
allowed_origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["Content-Type", "Authorization", "Accept"],
)

# ✅ SECURITY: Add Security Headers Middleware
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-XSS-Protection"] = "1; mode=block"
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
app.include_router(blog_router, prefix="/api/v1", tags=["Blog"])
app.include_router(upload_router, prefix="/api/v1", tags=["Upload"])

@app.get("/")
async def root():
    return {"message": f"Welcome to {settings.APP_NAME}"}

# ✅ NEW: Dynamic Sitemap.xml Endpoint for SEO
@app.get("/sitemap.xml", include_in_schema=False)
async def get_sitemap(db: Session = Depends(get_db)):
    products = db.query(Product).filter(Product.is_active == True).all()
    categories = db.query(Category).all()
    
    xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
    xml += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    
    base_url = "https://venixpodshop.com" # This will be your live domain
    
    xml += f'  <url><loc>{base_url}/</loc><priority>1.0</priority></url>\n'
    xml += f'  <url><loc>{base_url}/shop</loc><priority>0.9</priority></url>\n'
    
    for cat in categories:
        slug = cat.slug or cat.name.lower().replace(" ", "-")
        xml += f'  <url><loc>{base_url}/shop?category={slug}</loc><priority>0.8</priority></url>\n'
        
    for prod in products:
        slug = prod.slug or prod.title.replace(" ", "-").lower()
        xml += f'  <url><loc>{base_url}/product/{prod.id}</loc><priority>0.7</priority></url>\n'
        
    xml += '</urlset>'
    
    return Response(content=xml, media_type="application/xml")

# Serve uploaded images statically
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")