# app/services/rag_service.py
from typing import List, Dict, Optional


class RAGService:
    """
    Retrieval-Augmented Generation (RAG) Service
    Combines document retrieval with LLM for enhanced responses
    """

    def __init__(self):
        # Import here to avoid circular imports
        from app.services.embedding_service import EmbeddingService
        from app.services.vector_database import VectorDatabase
        from app.services.llm_service import LLMService
        
        self.embedding_service = EmbeddingService()
        self.vector_db = VectorDatabase()
        self.llm_service = LLMService()

    def add_document(self, document_id: int, content: str, metadata: Optional[Dict] = None):
        """Add a document to the vector database"""
        try:
            # Get embeddings for the document
            embeddings = self.embedding_service.embed_text(content)

            # Store in vector database
            self.vector_db.add_document(
                document_id=document_id,
                content=content,
                embeddings=embeddings,
                metadata=metadata or {}
            )
            return True
        except Exception as e:
            print(f"Error adding document to RAG: {e}")
            return False

    def search(self, query: str, top_k: int = 5) -> List[Dict]:
        """Search for relevant documents"""
        try:
            # Get query embeddings
            query_embeddings = self.embedding_service.embed_text(query)

            # Search in vector database
            results = self.vector_db.search(query_embeddings, top_k=top_k)
            return results
        except Exception as e:
            print(f"Error searching documents: {e}")
            return []

    def generate_response(
        self,
        query: str,
        conversation_history: Optional[List[Dict]] = None,
        top_k: int = 5
    ) -> str:
        """Generate response using RAG pipeline"""
        try:
            # Search for relevant context
            search_results = self.search(query, top_k=top_k)

            # Build context from search results
            context = "\n\n".join([
                f"Document {i+1}: {result.get('content', '')}"
                for i, result in enumerate(search_results)
            ]) if search_results else "No relevant documents found."

            # Generate response using LLM with context
            response = self.llm_service.generate_rag_response(
                query=query,
                context=context,
                conversation_history=conversation_history
            )
            return response
        except Exception as e:
            print(f"Error generating RAG response: {e}")
            return "I'm having trouble generating a response right now."

    def generate_title(self, first_message: str) -> str:
        """Generate a title for the conversation"""
        return self.llm_service.generate_conversation_title(first_message)