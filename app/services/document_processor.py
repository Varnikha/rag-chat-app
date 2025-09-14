import os
from pathlib import Path

# PDF + DOCX libraries
import docx
from PyPDF2 import PdfReader


class DocumentProcessor:
    """Extract text from uploaded documents"""

    def extract_text(self, file_path: str) -> str:
        """Extract text from .txt, .pdf, or .docx files"""
        try:
            ext = Path(file_path).suffix.lower()

            if ext == ".txt":
                return self._extract_txt(file_path)

            elif ext == ".pdf":
                return self._extract_pdf(file_path)

            elif ext == ".docx":
                return self._extract_docx(file_path)

            else:
                raise ValueError(f"Unsupported file type: {ext}")

        except Exception as e:
            print(f"❌ Error extracting text from {file_path}: {e}")
            return ""

    def process_document_for_rag(self, document_id: int):
        """Process document and add to RAG - imports moved inside"""
        # Import here to avoid circular imports
        from app.database import get_db
        from app.models.document import Document
        from app.services.rag_service import RAGService
        
        db = next(get_db())
        document = db.query(Document).filter(Document.id == document_id).first()
        
        if not document:
            return {"error": "Document not found"}
            
        # Extract text
        text = self.extract_text(document.file_path)
        if not text:
            return {"error": "Could not extract text"}
            
        # Process with RAG
        rag_service = RAGService()
        chunks, success = rag_service.process_and_embed_document(document, text, db)
        
        if success:
            document.processed = True
            db.commit()
            return {"success": True, "chunks": len(chunks)}
        else:
            return {"error": "Failed to create embeddings"}

    # Your existing extract methods stay the same...
    def _extract_txt(self, file_path: str) -> str:
        """Extract text from .txt"""
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()

    def _extract_pdf(self, file_path: str) -> str:
        """Extract text from .pdf"""
        text = []
        reader = PdfReader(file_path)
        for page in reader.pages:
            content = page.extract_text()
            if content:
                text.append(content)
        return "\n".join(text)

    def _extract_docx(self, file_path: str) -> str:
        """Extract text from .docx"""
        text = []
        doc = docx.Document(file_path)
        for para in doc.paragraphs:
            if para.text.strip():
                text.append(para.text)
        return "\n".join(text)