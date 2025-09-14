
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from typing import List, Optional
import os
import shutil
from pathlib import Path

# Import dependencies
from app.database import get_db
from app.routers.auth import get_current_user  # Fixed import - removed get_current_user_optional

router = APIRouter(prefix="/api/documents", tags=["documents"])

@router.get("/test")
async def test_documents():
    """Test endpoint to check if documents router works"""
    return {
        "message": "Documents router is working!", 
        "status": "success",
        "service": "documents"
    }

@router.get("/")
async def documents_status():
    """Check documents service status"""
    return {
        "service": "documents",
        "status": "connected",
        "message": "Documents service is running"
    }

@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    current_user = Depends(get_current_user),  # This requires authentication
    db: Session = Depends(get_db)
):
    """Upload a document (requires authentication)"""
    try:
        # Check file type
        allowed_extensions = {'.txt', '.pdf', '.docx', '.md'}
        file_extension = Path(file.filename).suffix.lower()
        
        if file_extension not in allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"File type {file_extension} not supported. Allowed: {allowed_extensions}"
            )
        
        # Create upload directory if it doesn't exist
        upload_dir = Path("uploads")
        upload_dir.mkdir(exist_ok=True)
        
        # Save file
        file_path = upload_dir / f"{current_user.id}_{file.filename}"
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        return {
            "message": "File uploaded successfully",
            "filename": file.filename,
            "size": file.size,
            "user": current_user.username,
            "file_path": str(file_path)
        }
        
    except Exception as e:
        print(f"Upload error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@router.get("/list")
async def list_documents(
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List user's uploaded documents"""
    try:
        upload_dir = Path("uploads")
        if not upload_dir.exists():
            return {"documents": []}
        
        # Find files belonging to current user
        user_files = []
        for file_path in upload_dir.glob(f"{current_user.id}_*"):
            if file_path.is_file():
                user_files.append({
                    "filename": file_path.name.replace(f"{current_user.id}_", ""),
                    "size": file_path.stat().st_size,
                    "created": file_path.stat().st_mtime
                })
        
        return {"documents": user_files}
        
    except Exception as e:
        print(f"List documents error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to list documents: {str(e)}")

print("✅ Documents router loaded successfully!")