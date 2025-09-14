import os
import hashlib
from typing import List, Dict, Optional, Tuple
import numpy as np
from sentence_transformers import SentenceTransformer
import openai
from sqlalchemy.orm import Session
from ..models.chunk import DocumentChunk
from ..models.document import Document

class EmbeddingService:
    """Handle text embeddings using multiple providers"""
    
    def __init__(self, provider: str = "sentence_transformers"):
        """
        Initialize embedding service
        
        Args:
            provider: "sentence_transformers" or "openai"
        """
        self.provider = provider
        
        if provider == "sentence_transformers":
            # Using a good free embedding model
            self.model = SentenceTransformer('all-MiniLM-L6-v2')
            self.embedding_dim = 384
            
        elif provider == "openai":
            # Requires OPENAI_API_KEY in environment
            openai.api_key = os.getenv("OPENAI_API_KEY")
            if not openai.api_key:
                raise ValueError("OPENAI_API_KEY environment variable required for OpenAI embeddings")
            self.embedding_dim = 1536  # text-embedding-ada-002 dimension
        
        else:
            raise ValueError(f"Unsupported embedding provider: {provider}")
    
    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for a single text"""
        if not text or not text.strip():
            return [0.0] * self.embedding_dim
        
        try:
            if self.provider == "sentence_transformers":
                embedding = self.model.encode(text.strip())
                return embedding.tolist()
                
            elif self.provider == "openai":
                response = openai.embeddings.create(
                    model="text-embedding-ada-002",
                    input=text.strip()
                )
                return response.data[0].embedding
                
        except Exception as e:
            print(f"Error generating embedding: {e}")
            return [0.0] * self.embedding_dim
    
    def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts"""
        if not texts:
            return []
        
        try:
            if self.provider == "sentence_transformers":
                # Clean texts
                clean_texts = [t.strip() if t and t.strip() else "empty" for t in texts]
                embeddings = self.model.encode(clean_texts)
                return embeddings.tolist()
                
            elif self.provider == "openai":
                # OpenAI has batch limits, process in chunks
                all_embeddings = []
                batch_size = 100
                
                for i in range(0, len(texts), batch_size):
                    batch = texts[i:i+batch_size]
                    clean_batch = [t.strip() if t and t.strip() else "empty" for t in batch]
                    
                    response = openai.embeddings.create(
                        model="text-embedding-ada-002",
                        input=clean_batch
                    )
                    
                    batch_embeddings = [data.embedding for data in response.data]
                    all_embeddings.extend(batch_embeddings)
                
                return all_embeddings
                
        except Exception as e:
            print(f"Error generating batch embeddings: {e}")
            return [[0.0] * self.embedding_dim] * len(texts)
    
    def calculate_similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """Calculate cosine similarity between two embeddings"""
        try:
            vec1 = np.array(embedding1)
            vec2 = np.array(embedding2)
            
            # Normalize vectors
            vec1_norm = vec1 / np.linalg.norm(vec1)
            vec2_norm = vec2 / np.linalg.norm(vec2)
            
            # Calculate cosine similarity
            similarity = np.dot(vec1_norm, vec2_norm)
            return float(similarity)
            
        except Exception as e:
            print(f"Error calculating similarity: {e}")
            return 0.0
    
    def get_embedding_hash(self, text: str) -> str:
        """Generate hash for embedding caching"""
        return hashlib.md5(f"{self.provider}_{text}".encode()).hexdigest()