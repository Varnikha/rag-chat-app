import os
import uuid
from typing import List, Dict, Optional, Tuple, Any
import chromadb
from chromadb.config import Settings
from sqlalchemy.orm import Session
from .embedding_service import EmbeddingService
from ..models.chunk import DocumentChunk
from ..models.document import Document

class VectorDatabase:
    """Handle vector database operations with ChromaDB"""
    
    def __init__(self, persist_directory: str = "data/chroma_db", embedding_provider: str = "sentence_transformers"):
        """Initialize ChromaDB client and embedding service"""
        
        # Create directory if it doesn't exist
        os.makedirs(persist_directory, exist_ok=True)
        
        # Initialize ChromaDB client
        self.client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(anonymized_telemetry=False)
        )
        
        # Initialize embedding service
        self.embedding_service = EmbeddingService(provider=embedding_provider)
        
        # Create or get collection
        self.collection = self.client.get_or_create_collection(
            name="document_chunks",
            metadata={"description": "Document chunks for RAG system"}
        )
        
        print(f"✅ Vector database initialized with {self.collection.count()} existing embeddings")
    
    def add_chunk_to_vector_db(self, chunk: DocumentChunk, db: Session) -> bool:
        """Add a single chunk to the vector database"""
        try:
            # Generate embedding
            embedding = self.embedding_service.generate_embedding(chunk.content)
            
            # Create unique ID for Chroma
            chroma_id = f"chunk_{chunk.id}_{uuid.uuid4().hex[:8]}"
            
            # Add to ChromaDB
            self.collection.add(
                embeddings=[embedding],
                documents=[chunk.content],
                metadatas=[{
                    "chunk_id": chunk.id,
                    "document_id": chunk.document_id,
                    "chunk_index": chunk.chunk_index,
                    "chunk_size": chunk.chunk_size,
                    "start_position": chunk.start_position,
                    "end_position": chunk.end_position
                }],
                ids=[chroma_id]
            )
            
            # Update chunk with embedding ID
            chunk.embedding_id = chroma_id
            db.commit()
            
            return True
            
        except Exception as e:
            print(f"Error adding chunk {chunk.id} to vector DB: {e}")
            return False
    
    def add_chunks_batch(self, chunks: List[DocumentChunk], db: Session) -> Tuple[int, int]:
        """Add multiple chunks to vector database in batch"""
        successful = 0
        failed = 0
        
        try:
            # Prepare data for batch insertion
            texts = [chunk.content for chunk in chunks]
            embeddings = self.embedding_service.generate_embeddings_batch(texts)
            
            chroma_ids = []
            documents = []
            metadatas = []
            valid_chunks = []
            
            for chunk, embedding in zip(chunks, embeddings):
                chroma_id = f"chunk_{chunk.id}_{uuid.uuid4().hex[:8]}"
                
                chroma_ids.append(chroma_id)
                documents.append(chunk.content)
                metadatas.append({
                    "chunk_id": chunk.id,
                    "document_id": chunk.document_id,
                    "chunk_index": chunk.chunk_index,
                    "chunk_size": chunk.chunk_size,
                    "start_position": chunk.start_position,
                    "end_position": chunk.end_position
                })
                
                valid_chunks.append(chunk)
            
            # Add to ChromaDB in batch
            self.collection.add(
                embeddings=embeddings,
                documents=documents,
                metadatas=metadatas,
                ids=chroma_ids
            )
            
            # Update chunks with embedding IDs
            for chunk, chroma_id in zip(valid_chunks, chroma_ids):
                chunk.embedding_id = chroma_id
            
            db.commit()
            successful = len(valid_chunks)
            
        except Exception as e:
            print(f"Error in batch embedding: {e}")
            failed = len(chunks)
        
        return successful, failed
    
    def search_similar_chunks(
        self, 
        query: str, 
        user_id: int, 
        db: Session, 
        limit: int = 5,
        similarity_threshold: float = 0.5
    ) -> List[Dict[str, Any]]:
        """Search for similar chunks using vector similarity"""
        
        try:
            # Generate query embedding
            query_embedding = self.embedding_service.generate_embedding(query)
            
            # Get user's document IDs for filtering
            user_doc_ids = db.query(Document.id).filter(Document.user_id == user_id).all()
            user_doc_ids = [doc_id[0] for doc_id in user_doc_ids]
            
            if not user_doc_ids:
                return []
            
            # Search in ChromaDB
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=min(limit * 2, 20),  # Get more results to filter by user
                include=["documents", "metadatas", "distances"]
            )
            
            # Process and filter results
            similar_chunks = []
            
            if results['documents'] and len(results['documents']) > 0:
                documents = results['documents'][0]
                metadatas = results['metadatas'][0]
                distances = results['distances'][0]
                
                for doc, metadata, distance in zip(documents, metadatas, distances):
                    # Convert distance to similarity (ChromaDB uses L2 distance)
                    similarity = 1 / (1 + distance)
                    
                    # Filter by user's documents and similarity threshold
                    if (metadata['document_id'] in user_doc_ids and 
                        similarity >= similarity_threshold):
                        
                        similar_chunks.append({
                            'chunk_id': metadata['chunk_id'],
                            'document_id': metadata['document_id'],
                            'content': doc,
                            'similarity': similarity,
                            'chunk_index': metadata['chunk_index'],
                            'metadata': metadata
                        })
                
                # Sort by similarity (highest first)
                similar_chunks.sort(key=lambda x: x['similarity'], reverse=True)
                
                # Limit results
                similar_chunks = similar_chunks[:limit]
            
            return similar_chunks
            
        except Exception as e:
            print(f"Error searching similar chunks: {e}")
            return []
    
    def delete_document_embeddings(self, document_id: int) -> bool:
        """Delete all embeddings for a document"""
        try:
            # Get all chunk embeddings for this document
            results = self.collection.get(
                where={"document_id": document_id},
                include=["metadatas"]
            )
            
            if results['ids']:
                # Delete embeddings
                self.collection.delete(ids=results['ids'])
                return True
            
            return True  # No embeddings to delete is also success
            
        except Exception as e:
            print(f"Error deleting embeddings for document {document_id}: {e}")
            return False
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics about the vector database"""
        try:
            count = self.collection.count()
            return {
                "total_embeddings": count,
                "collection_name": self.collection.name,
                "embedding_dimension": self.embedding_service.embedding_dim,
                "embedding_provider": self.embedding_service.provider
            }
        except Exception as e:
            print(f"Error getting collection stats: {e}")
            return {"error": str(e)}