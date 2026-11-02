# app/api/v1/upload.py
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
import os
import uuid
import shutil
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
    current_user: User = Depends(require_admin)
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file selected")
    
    # 1. Strict Extension Check
    ext = file.filename.rsplit(".", 1)[-1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Invalid file type. Allowed: png, jpg, jpeg, webp")

    # 2. Secure Filename Generation
    filename = f"{uuid.uuid4()}.{ext}"
    filepath = os.path.join(UPLOAD_DIR, filename)
    
    # ✅ STREAMING FIX: Write to disk in 1MB chunks. 
    # This prevents memory spikes and stops ParsPack/Nginx from timing out/hanging.
    file_size = 0
    with open(filepath, "wb") as buffer:
        while chunk := await file.read(1024 * 1024): # Read 1MB at a time
            file_size += len(chunk)
            if file_size > MAX_FILE_SIZE:
                buffer.close()
                os.remove(filepath) # Clean up the partial file
                raise HTTPException(status_code=400, detail="File too large. Maximum size is 5MB")
            buffer.write(chunk)
    
    # Return the URL path
    return {"url": f"/uploads/{filename}"}