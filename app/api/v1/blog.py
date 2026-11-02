# app/api/v1/blog.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.db.session import get_db
from app.core.dependencies import require_admin, get_current_user
from app.models.user import User
from app.models.blog import Blog
from app.schemas.blog import BlogCreate, BlogUpdate, BlogResponse

router = APIRouter(prefix="/blog", tags=["Blog"])

@router.get("/", response_model=List[BlogResponse])
def get_public_blogs(db: Session = Depends(get_db)):
    blogs = db.query(Blog).filter(Blog.is_active == True).order_by(Blog.created_at.desc()).all()
    return blogs

@router.get("/admin", response_model=List[BlogResponse])
def get_all_blogs_admin(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if not getattr(current_user, "is_admin", False):
        raise HTTPException(status_code=403, detail="Not authorized")
    blogs = db.query(Blog).order_by(Blog.created_at.desc()).all()
    return blogs

@router.post("/", response_model=BlogResponse)
def create_blog(blog_data: BlogCreate, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    new_blog = Blog(
        title=blog_data.title,
        content=blog_data.content,
        image_url=blog_data.image_url,
        is_active=blog_data.is_active,
        meta_title=blog_data.meta_title,
        meta_description=blog_data.meta_description,
        image_alt_text=blog_data.image_alt_text
    )
    db.add(new_blog)
    db.commit()
    db.refresh(new_blog)
    return new_blog

@router.put("/{blog_id}", response_model=BlogResponse)
def update_blog(blog_id: int, blog_data: BlogUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if not getattr(current_user, "is_admin", False):
        raise HTTPException(status_code=403, detail="Not authorized")
        
    blog = db.query(Blog).filter(Blog.id == blog_id).first()
    if not blog:
        raise HTTPException(status_code=404, detail="Blog not found")
    
    if blog_data.title is not None: blog.title = blog_data.title
    if blog_data.content is not None: blog.content = blog_data.content
    if blog_data.image_url is not None: blog.image_url = blog_data.image_url
    if blog_data.is_active is not None: blog.is_active = blog_data.is_active
    if blog_data.meta_title is not None: blog.meta_title = blog_data.meta_title
    if blog_data.meta_description is not None: blog.meta_description = blog_data.meta_description
    if blog_data.image_alt_text is not None: blog.image_alt_text = blog_data.image_alt_text
    
    db.commit()
    db.refresh(blog)
    return blog

@router.delete("/{blog_id}")
def delete_blog(blog_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    blog = db.query(Blog).filter(Blog.id == blog_id).first()
    if not blog:
        raise HTTPException(status_code=404, detail="Blog not found")
    
    db.delete(blog)
    db.commit()
    return {"message": "Blog deleted successfully"}

@router.get("/{blog_id}")
def get_single_blog(blog_id: int, db: Session = Depends(get_db)):
    blog = db.query(Blog).filter(Blog.id == blog_id, Blog.is_active == True).first()
    if not blog:
        raise HTTPException(status_code=404, detail="Blog not found")
    return blog