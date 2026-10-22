
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from typing import List, Optional
import os
import shutil
from pathlib import Path

# Import dependencies
from app.database import get_db, Document
from app.routers.auth import get_current_user
from app.services.document_processor import DocumentProcessor
from app.services.vector_database import VectorDatabase

router = APIRouter(tags=["documents"])

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
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload a document, parse it, and index it for RAG retrieval."""
    try:
        allowed_extensions = {'.txt', '.pdf', '.docx', '.md'}
        file_extension = Path(file.filename).suffix.lower()

        if file_extension not in allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"File type {file_extension} not supported. Allowed: {allowed_extensions}"
            )

        upload_dir = Path("uploads")
        upload_dir.mkdir(exist_ok=True)

        contents = await file.read()
        file_path = upload_dir / f"{current_user.id}_{file.filename}"
        with open(file_path, "wb") as buffer:
            buffer.write(contents)

        processor = DocumentProcessor()
        document, text_content, chunks = processor.process_document(
            file_content=contents,
            filename=file.filename,
            user_id=current_user.id,
            db=db,
            create_chunks=True,
        )

        vector_db = VectorDatabase()
        indexed = 0
        for chunk in chunks:
            ok = vector_db.add_chunk_to_vector_db(chunk, db)
            if ok:
                indexed += 1

        return {
            "message": "File uploaded and indexed successfully",
            "filename": file.filename,
            "size": len(contents),
            "user": current_user.username,
            "file_path": str(file_path),
            "document_id": document.id,
            "chunks_created": len(chunks),
            "chunks_indexed": indexed,
            "content_preview": text_content[:300],
        }

    except Exception as e:
        print(f"Upload error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@router.get("/list")
async def list_documents(
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List user's uploaded documents."""
    try:
        documents = db.query(Document).filter(Document.user_id == current_user.id).all()
        response = [
            {
                "id": doc.id,
                "filename": doc.filename,
                "size": doc.file_size,
                "uploaded_at": doc.uploaded_at.isoformat() if doc.uploaded_at else None,
                "processed": doc.processed,
            }
            for doc in documents
        ]
        return {"documents": response}

    except Exception as e:
        print(f"List documents error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to list documents: {str(e)}")

print("✅ Documents router loaded successfully!")