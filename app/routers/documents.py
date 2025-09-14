# app/routers/documents.py (Enhanced Version)

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import List, Optional
import os
import shutil
from pathlib import Path
import uuid
from datetime import datetime

from app.models.database import get_db, Document, User
from app.routers.auth import get_current_user

router = APIRouter(tags=["documents"])

# Response models
class DocumentResponse(BaseModel):
    id: int
    filename: str
    file_size: int
    upload_date: datetime
    content_type: Optional[str]
    processing_status: str = "completed"

class DocumentUploadResponse(BaseModel):
    message: str
    document_id: int
    filename: str
    file_path: str
    processing_started: bool

class DocumentSearchRequest(BaseModel):
    query: str
    top_k: Optional[int] = 5

class DocumentSearchResponse(BaseModel):
    results: List[dict]
    query: str
    total_results: int

# Create upload directory
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

# Allowed file types and size limits
ALLOWED_EXTENSIONS = {'.pdf', '.txt', '.docx', '.md', '.csv', '.json'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload and process document with authentication"""
    
    # Validate file
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")
    
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400, 
            detail=f"File type {file_ext} not supported. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    
    # Check file size
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large. Maximum size: 10MB")
    
    try:
        # Generate unique filename
        unique_filename = f"{uuid.uuid4()}_{file.filename}"
        file_path = UPLOAD_DIR / unique_filename
        
        # Save file to disk
        with open(file_path, "wb") as buffer:
            buffer.write(content)
        
        # Save to database
        db_document = Document(
            filename=file.filename,
            file_path=str(file_path),
            file_size=len(content),
            user_id=current_user.id,
            content_type=file.content_type,
            upload_date=datetime.utcnow()
        )
        
        db.add(db_document)
        db.commit()
        db.refresh(db_document)
        
        # Process document in background
        background_tasks.add_task(process_document_async, db_document.id, str(file_path))
        
        return DocumentUploadResponse(
            message="File uploaded successfully and processing started",
            document_id=db_document.id,
            filename=file.filename,
            file_path=str(file_path),
            processing_started=True
        )
        
    except Exception as e:
        # Clean up file if database save failed
        if file_path.exists():
            file_path.unlink()
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@router.get("/list", response_model=List[DocumentResponse])
async def list_documents(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get list of user's documents"""
    try:
        documents = db.query(Document).filter(Document.user_id == current_user.id).all()
        
        return [
            DocumentResponse(
                id=doc.id,
                filename=doc.filename,
                file_size=doc.file_size,
                upload_date=doc.upload_date,
                content_type=doc.content_type,
                processing_status="completed"  # You can add a processing_status field to Document model
            )
            for doc in documents
        ]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch documents: {str(e)}")

@router.delete("/delete/{document_id}")
async def delete_document(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a document"""
    try:
        document = db.query(Document).filter(
            Document.id == document_id,
            Document.user_id == current_user.id
        ).first()
        
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Delete file from disk
        file_path = Path(document.file_path)
        if file_path.exists():
            file_path.unlink()
        
        # Delete from database
        db.delete(document)
        db.commit()
        
        # TODO: Delete from vector database
        try:
            from app.services.rag_service import RAGService
            rag_service = RAGService()
            await rag_service.delete_document_embeddings(document_id)
        except Exception as e:
            print(f"Warning: Could not delete embeddings: {e}")
        
        return {"message": "Document deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete document: {str(e)}")

@router.post("/search", response_model=DocumentSearchResponse)
async def search_documents(
    search_request: DocumentSearchRequest,
    current_user: User = Depends(get_current_user)
):
    """Search through user's documents"""
    try:
        from app.services.rag_service import RAGService
        rag_service = RAGService()
        
        results = await rag_service.search_documents(
            query=search_request.query,
            user_id=current_user.id,
            top_k=search_request.top_k
        )
        
        return DocumentSearchResponse(
            results=results,
            query=search_request.query,
            total_results=len(results)
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

@router.get("/stats")
async def get_document_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get document statistics for the user"""
    try:
        total_docs = db.query(Document).filter(Document.user_id == current_user.id).count()
        total_size = db.query(Document).filter(Document.user_id == current_user.id).with_entities(
            db.func.sum(Document.file_size)
        ).scalar() or 0
        
        return {
            "total_documents": total_docs,
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")

# Background processing function
async def process_document_async(document_id: int, file_path: str):
    """Process document using RAG pipeline"""
    try:
        from app.models import get_db
        from app.services.rag_service import RAGService
        
        db = next(get_db())
        document = db.query(Document).filter(Document.id == document_id).first()
        
        if not document:
            print(f"Document {document_id} not found")
            return
        
        # Read file content based on type
        content = ""
        file_ext = Path(file_path).suffix.lower()
        
        if file_ext == '.txt' or file_ext == '.md':
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        elif file_ext == '.pdf':
            # Use your PDF processing logic here
            from app.services.document_processor import DocumentProcessor
            processor = DocumentProcessor()
            content = processor.extract_text_from_pdf(file_path)
        else:
            # For other formats, try reading as text
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
            except:
                print(f"Could not read file {file_path}")
                return
        
        # Process with RAG service
        rag_service = RAGService()
        success = await rag_service.process_and_embed_document(document, content, db)
        
        print(f"Document {document_id} processed: {'✅ Success' if success else '❌ Failed'}")
        
    except Exception as e:
        print(f"❌ Document processing failed for {document_id}: {e}")

# Test endpoints
@router.get("/test")
async def test_documents():
    """Test endpoint"""
    return {"message": "✅ Documents router is working!"}

@router.get("/test-auth")
async def test_documents_auth(current_user: User = Depends(get_current_user)):
    """Test authenticated endpoint"""
    return {
        "message": f"✅ Documents auth working! Hello {current_user.username}",
        "user_id": current_user.id
    }