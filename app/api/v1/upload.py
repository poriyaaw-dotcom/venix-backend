# app/api/v1/upload.py
from fastapi import APIRouter, UploadFile, File, HTTPException
import os
import uuid

router = APIRouter(prefix="/upload", tags=["Upload"])

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/image")
async def upload_image(file: UploadFile = File(...)):
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")
    
    # Generate a unique filename to prevent overwriting
    ext = file.filename.split(".")[-1] if "." in file.filename else "jpg"
    filename = f"{uuid.uuid4()}.{ext}"
    filepath = os.path.join(UPLOAD_DIR, filename)
    
    # Save the file
    with open(filepath, "wb") as buffer:
        buffer.write(await file.read())
    
    # Return the URL path (FastAPI will serve this via static mount)
    return {"url": f"/uploads/{filename}"}
