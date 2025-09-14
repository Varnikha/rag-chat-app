from typing import List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from .vector_database import VectorDatabase
from .text_chunker import TextChunker
from ..models.chunk import DocumentChunk
from app.database import get_db  # ✅ Correct
from app.models.database import Document

class RAGService:
    """Main service for RAG operations"""
    
    def __init__(self, embedding_provider: str = "sentence_transformers"):
        self.vector_db = VectorDatabase(embedding_provider=embedding_provider)
        self.chunker = TextChunker()
    
    def process_and_embed_document(self, document: Document, text: str, db: Session) -> Tuple[List[DocumentChunk], bool]:
        """Process document text into chunks and create embeddings"""
        
        print(f"Processing document {document.id}: {document.filename}")
        
        # Create chunks
        chunks = self.chunker.process_document_chunks(document.id, text, db)
        print(f"Created {len(chunks)} chunks")
        
        # Create embeddings
        if chunks:
            successful, failed = self.vector_db.add_chunks_batch(chunks, db)
            print(f"Embeddings: {successful} successful, {failed} failed")
            
            return chunks, failed == 0
        
        return [], True
    
    def search_relevant_chunks(
        self, 
        query: str, 
        user_id: int, 
        db: Session,
        top_k: int = 5,
        similarity_threshold: float = 0.5
    ) -> List[Dict[str, Any]]:
        """Search for relevant chunks for a query"""
        
        return self.vector_db.search_similar_chunks(
            query=query,
            user_id=user_id,
            db=db,
            limit=top_k,
            similarity_threshold=similarity_threshold
        )
    
    def get_context_for_query(self, query: str, user_id: int, db: Session, max_context_length: int = 4000) -> str:
        """Get relevant context for RAG query"""
        
        # Search for relevant chunks
        relevant_chunks = self.search_relevant_chunks(query, user_id, db)
        
        # Combine chunks into context
        context_parts = []
        current_length = 0
        
        for chunk_data in relevant_chunks:
            content = chunk_data['content']
            if current_length + len(content) <= max_context_length:
                context_parts.append(f"[Doc {chunk_data['document_id']}]: {content}")
                current_length += len(content)
            else:
                break
        
        return "\n\n".join(context_parts)
    
    def delete_document_from_rag(self, document_id: int, db: Session) -> bool:
        """Remove document and its embeddings from RAG system"""
        
        # Delete from vector database
        vector_success = self.vector_db.delete_document_embeddings(document_id)
        
        # Delete chunks from SQL database
        db.query(DocumentChunk).filter(DocumentChunk.document_id == document_id).delete()
        db.commit()
        
        return vector_success
    
    def get_rag_stats(self) -> Dict[str, Any]:
        """Get RAG system statistics"""
        return self.vector_db.get_collection_stats()
    async def get_response(self, query: str, user_id: int) -> str:
        """Get RAG response for a query"""
        from app.database import get_db
        from app.services.llm_service import LLMService
        
        # Get database session
        db = next(get_db())
        
        try:
            # Get context from your documents
            context = self.get_context_for_query(query, user_id, db)
            
            # Initialize LLM service
            llm_service = LLMService()
            
            # Generate response
            if context:
                response = llm_service.generate_rag_response(query, context)
            else:
                response = "I don't have any relevant documents to answer your question. Please upload some documents first."
            
            return response
            
        finally:
            db.close()