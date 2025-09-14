from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.security import HTTPBearer
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import List
import os
import shutil
from pathlib import Path
import uuid

router = APIRouter(tags=["documents"])
security = HTTPBearer()

# =========================
# Response Models
# =========================
class DocumentResponse(BaseModel):
    id: int
    filename: str
    file_size: int
    uploaded_at: str
    processed: bool


class DocumentUploadResponse(BaseModel):
    message: str
    document_id: int
    filename: str
    file_path: str


# =========================
# Upload Directory
# =========================
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)


# =========================
# Database Dependency
# =========================
def get_database():
    from app.database import get_db
    return next(get_db())


# =========================
# Upload Endpoint
# =========================
@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_database)
):
    """Upload and process document"""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    allowed_types = [".pdf", ".txt", ".docx"]
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in allowed_types:
        raise HTTPException(status_code=400, detail="File type not supported")

    try:
        # Generate unique filename
        unique_filename = f"{uuid.uuid4()}_{file.filename}"
        file_path = UPLOAD_DIR / unique_filename

        # Save file to disk
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # File size
        file_size = os.path.getsize(file_path)

        # Save to DB
        from app.models.user import Document
        from datetime import datetime

        db_document = Document(
            filename=file.filename,
            file_path=str(file_path),
            file_size=file_size,
            user_id=1,  # TODO: replace with JWT user later
            uploaded_at=datetime.utcnow(),
            processed=False,
        )

        db.add(db_document)
        db.commit()
        db.refresh(db_document)

        # Process document asynchronously
        await process_document_async(db_document.id, str(file_path), db)

        return {
            "message": "File uploaded and processing started",
            "document_id": db_document.id,
            "filename": file.filename,
            "file_path": str(file_path),
        }

    except Exception as e:
        if file_path.exists():
            file_path.unlink()
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


# =========================
# List Documents
# =========================
@router.get("/list", response_model=List[DocumentResponse])
async def list_documents(db: Session = Depends(get_database)):
    """Get list of user's documents"""
    try:
        from app.models.user import Document

        documents = db.query(Document).filter(Document.user_id == 1).all()

        return [
            DocumentResponse(
                id=doc.id,
                filename=doc.filename,
                file_size=doc.file_size,
                uploaded_at=doc.uploaded_at.isoformat(),
                processed=doc.processed,
            )
            for doc in documents
        ]

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch documents: {str(e)}")


# =========================
# Process Document
# =========================
async def process_document_async(document_id: int, file_path: str, db: Session):
    """Process document using DocumentProcessor + RAGService"""
    try:
        from app.models.user import Document
        from app.services.document_processor import DocumentProcessor
        from app.services.rag_service import RAGService

        # Get document from DB
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            print(f"Document {document_id} not found")
            return

        # Extract text
        processor = DocumentProcessor()
        text_content = processor.extract_text(file_path)

        if not text_content or text_content.strip() == "":
            print(f"No text extracted from {file_path}")
            document.processed = False
            db.commit()
            return

        # Embed with RAG
        rag_service = RAGService()
        chunks, success = rag_service.process_and_embed_document(document, text_content, db)

        document.processed = success
        db.commit()

        print(f"Document {document_id} processed successfully: {success}")

    except Exception as e:
        print(f"Document processing failed: {e}")
        from app.models.user import Document
        document = db.query(Document).filter(Document.id == document_id).first()
        if document:
            document.processed = False
            db.commit()
