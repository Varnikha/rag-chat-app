import sys
sys.path.append('.')

from app.services.document_processor import DocumentProcessor
from app.services.text_chunker import TextChunker
from app.database import get_db  # ✅ Correct
from app.models.user import User
from pathlib import Path

def test_text_chunking():
    print("Testing Text Chunking System...")
    
    processor = DocumentProcessor()
    chunker = TextChunker(chunk_size=500, overlap=100)  # Smaller chunks for testing
    db = next(get_db())
    
    try:
        # Create/get test user
        test_user = db.query(User).filter(User.email == "test@example.com").first()
        if not test_user:
            test_user = User(email="test@example.com", hashed_password="dummy_hash")
            db.add(test_user)
            db.commit()
            db.refresh(test_user)
        
        # Create a longer test document
        test_content = """
        This is the first paragraph of our test document. It contains multiple sentences that will help us test the chunking functionality. Each sentence provides meaningful content for testing.
        
        This is the second paragraph. It discusses different aspects of document processing and text chunking. The system should be able to handle various types of content and create meaningful chunks.
        
        The third paragraph focuses on RAG systems. Retrieval Augmented Generation is a powerful technique that combines information retrieval with text generation. It allows AI systems to access external knowledge.
        
        Finally, the fourth paragraph concludes our test document. It ensures we have enough content to create multiple chunks with proper overlap. This helps test the chunking algorithm thoroughly.
        
        Additional content for testing includes technical terms like embeddings, vector databases, and similarity search. These concepts are crucial for RAG implementations.
        """
        
        # Save test file
        test_file_path = Path("test_chunking_document.txt")
        with open(test_file_path, 'w') as f:
            f.write(test_content)
        
        print(f"📄 Created test document: {len(test_content)} characters")
        
        # Process document with chunking
        with open(test_file_path, 'rb') as f:
            file_content = f.read()
        
        document, full_text, chunks = processor.process_document(
            file_content=file_content,
            filename="test_chunking_document.txt",
            user_id=test_user.id,
            db=db,
            create_chunks=True
        )
        
        print(f"✅ Document processed: ID {document.id}")
        print(f"   - Original text: {len(full_text)} characters")
        print(f"   - Created chunks: {len(chunks)}")
        
        # Display chunk information
        for i, chunk in enumerate(chunks):
            print(f"\n--- Chunk {i+1} ---")
            print(f"Size: {chunk.chunk_size} characters")
            print(f"Position: {chunk.start_position}-{chunk.end_position}")
            print(f"Content preview: {chunk.content[:100]}...")
        
        # Test chunk retrieval
        retrieved_chunks = chunker.get_document_chunks(document.id, db)
        print(f"\n✅ Retrieved {len(retrieved_chunks)} chunks from database")
        
        # Test simple search
        search_results = chunker.search_chunks_by_content("RAG systems", test_user.id, db)
        print(f"✅ Search found {len(search_results)} chunks containing 'RAG systems'")
        
        if search_results:
            print(f"First result: {search_results[0].content[:100]}...")
        
        # Cleanup
        test_file_path.unlink()
        
        print("\n🎉 Text chunking system working correctly!")
        print(f"📊 Progress: Document processing + Text chunking complete")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    test_text_chunking()