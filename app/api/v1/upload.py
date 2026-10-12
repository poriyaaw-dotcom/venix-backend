# app/api/v1/upload.py
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
import os
import uuid
from app.core.dependencies import require_admin
from app.models.user import User

router = APIRouter(prefix="/upload", tags=["Upload"])

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# ✅ SECURITY FIX: Strict allowed extensions and file size limit
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB

@router.post("/image")
async def upload_image(
    file: UploadFile = File(...),
    current_user: User = Depends(require_admin)  # ✅ Only admins can upload
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file selected")
    
    # 1. Strict Extension Check (Prevents spoofed content-types)
    ext = file.filename.rsplit(".", 1)[-1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Invalid file type. Allowed: png, jpg, jpeg, webp")

    # 2. File Size Check (Prevents server crash / DoS attacks)
    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large. Maximum size is 5MB")

    # 3. Secure Filename Generation
    filename = f"{uuid.uuid4()}.{ext}"
    filepath = os.path.join(UPLOAD_DIR, filename)
    
    # Save the file
    with open(filepath, "wb") as buffer:
        buffer.write(contents)
    
    # Return the URL path
    return {"url": f"/uploads/{filename}"}