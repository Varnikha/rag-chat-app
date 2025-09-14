import re
from typing import List, Dict, Tuple
from sqlalchemy.orm import Session
from ..models.chunk import DocumentChunk
from app.database import get_db  # ✅ Correct

class TextChunker:
    """Handle text chunking for RAG system"""
    
    def __init__(self, chunk_size: int = 1000, overlap: int = 200):
        self.chunk_size = chunk_size
        self.overlap = overlap
    
    def clean_text(self, text: str) -> str:
        """Clean and normalize text"""
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        # Remove special characters but keep punctuation
        text = re.sub(r'[^\w\s\.\,\!\?\;\:\-\(\)]', '', text)
        return text.strip()
    
    def split_by_sentences(self, text: str) -> List[str]:
        """Split text into sentences for better chunking"""
        # Simple sentence splitting (can be improved with nltk/spacy)
        sentences = re.split(r'(?<=[.!?])\s+', text)
        return [s.strip() for s in sentences if s.strip()]
    
    def create_chunks(self, text: str) -> List[Dict]:
        """Create overlapping chunks from text"""
        cleaned_text = self.clean_text(text)
        sentences = self.split_by_sentences(cleaned_text)
        
        if not sentences:
            return []
        
        chunks = []
        current_chunk = ""
        current_position = 0
        chunk_start_position = 0
        
        for sentence in sentences:
            # Check if adding this sentence exceeds chunk size
            potential_chunk = current_chunk + " " + sentence if current_chunk else sentence
            
            if len(potential_chunk) <= self.chunk_size:
                current_chunk = potential_chunk
            else:
                # Save current chunk if it has content
                if current_chunk:
                    chunks.append({
                        'content': current_chunk,
                        'start_position': chunk_start_position,
                        'end_position': chunk_start_position + len(current_chunk),
                        'size': len(current_chunk)
                    })
                
                # Start new chunk with overlap
                if len(chunks) > 0 and self.overlap > 0:
                    # Create overlap from previous chunk
                    overlap_text = current_chunk[-self.overlap:] if len(current_chunk) > self.overlap else current_chunk
                    current_chunk = overlap_text + " " + sentence
                    chunk_start_position = chunks[-1]['end_position'] - len(overlap_text)
                else:
                    current_chunk = sentence
                    chunk_start_position = current_position
            
            current_position += len(sentence) + 1  # +1 for space
        
        # Add final chunk
        if current_chunk:
            chunks.append({
                'content': current_chunk,
                'start_position': chunk_start_position,
                'end_position': chunk_start_position + len(current_chunk),
                'size': len(current_chunk)
            })
        
        return chunks
    
    def process_document_chunks(self, document_id: int, text: str, db: Session) -> List[DocumentChunk]:
        """Create and store chunks for a document"""
        
        # Delete existing chunks for this document
        db.query(DocumentChunk).filter(DocumentChunk.document_id == document_id).delete()
        
        # Create new chunks
        chunks_data = self.create_chunks(text)
        chunk_objects = []
        
        for index, chunk_data in enumerate(chunks_data):
            chunk = DocumentChunk(
                document_id=document_id,
                chunk_index=index,
                content=chunk_data['content'],
                chunk_size=chunk_data['size'],
                start_position=chunk_data['start_position'],
                end_position=chunk_data['end_position']
            )
            db.add(chunk)
            chunk_objects.append(chunk)
        
        db.commit()
        
        # Refresh all chunk objects
        for chunk in chunk_objects:
            db.refresh(chunk)
        
        return chunk_objects
    
    def get_document_chunks(self, document_id: int, db: Session) -> List[DocumentChunk]:
        """Get all chunks for a document"""
        return db.query(DocumentChunk).filter(
            DocumentChunk.document_id == document_id
        ).order_by(DocumentChunk.chunk_index).all()
    
    def search_chunks_by_content(self, query: str, user_id: int, db: Session, limit: int = 5) -> List[DocumentChunk]:
        """Simple text-based search in chunks (will be replaced by vector search)"""
        # Join with documents to filter by user
        chunks = db.query(DocumentChunk).join(Document).filter(
            Document.user_id == user_id,
            DocumentChunk.content.ilike(f"%{query}%")
        ).limit(limit).all()
        
        return chunks