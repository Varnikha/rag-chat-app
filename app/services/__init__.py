from .text_chunker import TextChunker
from .embedding_service import EmbeddingService
from .vector_database import VectorDatabase

# RAGService is imported only when needed to avoid circular imports
def get_rag_service():
    from .rag_service import RAGService
    return RAGService