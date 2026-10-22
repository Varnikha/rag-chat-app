import os
import re
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
        self.persist_directory = persist_directory
        os.makedirs(self.persist_directory, exist_ok=True)
        self.client = chromadb.PersistentClient(
            path=self.persist_directory,
            settings=Settings(anonymized_telemetry=False)
        )
        self.embedding_service = EmbeddingService(provider=embedding_provider)
        self.collection = self._get_or_create_collection()
        print(f"✅ Vector database initialized with {self.collection.count()} existing embeddings")

    def _get_or_create_collection(self):
        """Create the collection, resetting stale Chroma metadata when the SQLite schema is outdated."""
        try:
            return self.client.get_or_create_collection(
                name="document_chunks",
                metadata={"description": "Document chunks for RAG system"}
            )
        except Exception as exc:
            error_message = str(exc).lower()
            if "no such column: collections.topic" in error_message or "database schema" in error_message or "sqlite" in error_message and "column" in error_message:
                print(f"⚠️ ChromaDB schema is stale. Resetting persisted vector database at {self.persist_directory}.")
                import shutil
                if os.path.exists(self.persist_directory):
                    shutil.rmtree(self.persist_directory)
                os.makedirs(self.persist_directory, exist_ok=True)
                self.client = chromadb.PersistentClient(
                    path=self.persist_directory,
                    settings=Settings(anonymized_telemetry=False)
                )
                return self.client.get_or_create_collection(
                    name="document_chunks",
                    metadata={"description": "Document chunks for RAG system"}
                )
            raise

    def _normalize_query_terms(self, query: str) -> List[str]:
        """Extract relevant query terms while removing stopwords and punctuation."""
        if not query:
            return []

        tokens = re.findall(r"[a-zA-Z0-9]+", query.lower())
        stop_words = {
            "the", "a", "an", "is", "are", "was", "were", "what", "when", "where",
            "who", "why", "how", "which", "this", "that", "these", "those", "for",
            "with", "from", "into", "about", "of", "in", "on", "to", "and", "or",
            "it", "its", "be", "as", "at", "by", "if", "then", "does", "do", "did",
            "can", "could", "should", "would", "using", "used", "tell", "me", "give",
            "show", "summarize", "please"
        }
        return [term for term in tokens if term not in stop_words and len(term) > 2]

    def search_keyword_chunks(
        self,
        query: str,
        user_id: int,
        db: Session,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """Fallback retrieval based on term overlap when semantic similarity is weak or empty."""
        query_terms = self._normalize_query_terms(query)
        if not query_terms:
            user_chunks = (
                db.query(DocumentChunk)
                .join(Document, Document.id == DocumentChunk.document_id)
                .filter(Document.user_id == user_id)
                .order_by(DocumentChunk.chunk_index)
                .limit(limit)
                .all()
            )
            return [{"content": chunk.content, "similarity": 0.0} for chunk in user_chunks]

        user_chunks = (
            db.query(DocumentChunk)
            .join(Document, Document.id == DocumentChunk.document_id)
            .filter(Document.user_id == user_id)
            .order_by(DocumentChunk.chunk_index)
            .all()
        )

        scored_chunks = []
        for chunk in user_chunks:
            content = (chunk.content or '').lower()
            if not content:
                continue
            matches = sum(1 for term in query_terms if term in content)
            if matches == 0:
                continue
            score = matches / max(len(query_terms), 1)
            scored_chunks.append({
                "chunk_id": chunk.id,
                "document_id": chunk.document_id,
                "content": chunk.content,
                "similarity": round(score, 4),
                "chunk_index": chunk.chunk_index,
                "metadata": {"document_id": chunk.document_id, "chunk_id": chunk.id},
            })

        scored_chunks.sort(key=lambda item: item["similarity"], reverse=True)
        return scored_chunks[:limit]

    def search_relevant_chunks(
        self,
        query: str,
        user_id: int,
        db: Session,
        limit: int = 5,
        similarity_threshold: float = 0.2,
    ) -> List[Dict[str, Any]]:
        """Search semantically first, then fall back to keyword-overlap retrieval."""
        vector_matches = self.search_similar_chunks(
            query=query,
            user_id=user_id,
            db=db,
            limit=limit,
            similarity_threshold=similarity_threshold,
        )
        if vector_matches:
            return vector_matches

        return self.search_keyword_chunks(query=query, user_id=user_id, db=db, limit=limit)
    
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
        similarity_threshold: float = 0.2
    ) -> List[Dict[str, Any]]:
        """Search for similar chunks using vector similarity."""
        try:
            query_embedding = self.embedding_service.generate_embedding(query)
            user_doc_ids = db.query(Document.id).filter(Document.user_id == user_id).all()
            user_doc_ids = [doc_id[0] for doc_id in user_doc_ids]

            if not user_doc_ids:
                return []

            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=min(limit * 3, 25),
                include=["documents", "metadatas", "distances"]
            )

            similar_chunks = []
            if results.get('documents') and len(results['documents']) > 0:
                documents = results['documents'][0]
                metadatas = results['metadatas'][0]
                distances = results['distances'][0]

                for doc, metadata, distance in zip(documents, metadatas, distances):
                    if not isinstance(metadata, dict):
                        continue

                    document_id = metadata.get('document_id')
                    if document_id not in user_doc_ids:
                        continue

                    try:
                        similarity = 1 / (1 + float(distance))
                    except (TypeError, ValueError):
                        similarity = 0.0

                    if similarity >= similarity_threshold:
                        similar_chunks.append({
                            'chunk_id': metadata.get('chunk_id'),
                            'document_id': document_id,
                            'content': doc,
                            'similarity': round(similarity, 4),
                            'chunk_index': metadata.get('chunk_index'),
                            'metadata': metadata,
                        })

                similar_chunks.sort(key=lambda x: x['similarity'], reverse=True)
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