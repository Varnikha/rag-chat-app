# app/models/document.py
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

# Pydantic models for API
class DocumentBase(BaseModel):
    filename: str
    content: str

class DocumentCreate(DocumentBase):
    pass

class DocumentResponse(DocumentBase):
    id: int
    user_id: int
    uploaded_at: datetime
    
    class Config:
        from_attributes = True

class DocumentUpload(BaseModel):
    filename: str
    content: str

# Export alias for backward compatibility
Document = DocumentResponse