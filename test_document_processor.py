import sys
sys.path.append('.')

from app.services.document_processor import DocumentProcessor
from app.database import get_db  # ✅ Correct
from app.models.user import User
from pathlib import Path

def test_document_processor():
    print("Testing Document Processor...")
    
    processor = DocumentProcessor()
    db = next(get_db())
    
    try:
        # Create a test user if doesn't exist
        test_user = db.query(User).filter(User.email == "test@example.com").first()
        if not test_user:
            test_user = User(email="test@example.com", hashed_password="dummy_hash")
            db.add(test_user)
            db.commit()
            db.refresh(test_user)
        
        # Create a simple test text file
        test_content = "This is a test document for RAG system testing.\nIt contains multiple lines of text.\nThis will be processed and stored in the vector database."
        test_file_path = Path("test_document.txt")
        
        with open(test_file_path, 'w') as f:
            f.write(test_content)
        
        # Test text extraction
        extracted_text = processor.extract_text(test_file_path)
        print(f"✅ Text extraction successful: {len(extracted_text)} characters")
        
        # Test document processing
        with open(test_file_path, 'rb') as f:
            file_content = f.read()
        
        document, full_text = processor.process_document(
            file_content=file_content,
            filename="test_document.txt",
            user_id=test_user.id,
            db=db
        )
        
        print(f"✅ Document processed: ID {document.id}")
        print(f"   - Filename: {document.filename}")
        print(f"   - File size: {document.file_size} bytes")
        print(f"   - Preview: {document.content_preview[:100]}...")
        
        # Test document retrieval
        user_docs = processor.get_user_documents(test_user.id, db)
        print(f"✅ User has {len(user_docs)} documents")
        
        # Cleanup test file
        test_file_path.unlink()
        
        print("\n🎉 Document processor working correctly!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    test_document_processor()