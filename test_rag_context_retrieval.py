import sys

sys.path.append('.')

from app.database import get_db, User, Document
from app.models.chunk import DocumentChunk
from app.services.vector_database import VectorDatabase


def test_search_relevant_chunks_falls_back_to_user_document_context():
    db = next(get_db())

    user = db.query(User).filter(User.email == 'rag_retrieval_test@example.com').first()
    if not user:
        user = User(email='rag_retrieval_test@example.com', hashed_password='dummy_hash')
        db.add(user)
        db.commit()
        db.refresh(user)

    doc = db.query(Document).filter(Document.user_id == user.id, Document.filename == 'claude_guide.txt').first()
    if not doc:
        doc = Document(
            filename='claude_guide.txt',
            file_path='uploads/claude_guide.txt',
            file_size=500,
            user_id=user.id,
            content='Claude Code is an AI coding assistant that helps developers write, review, and refactor code. It supports Python, JavaScript, and backend APIs.',
            content_preview='Claude Code is an AI coding assistant.',
            processed=True,
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)

    chunk = db.query(DocumentChunk).filter(DocumentChunk.document_id == doc.id).first()
    if not chunk:
        chunk = DocumentChunk(
            document_id=doc.id,
            chunk_index=0,
            content='Claude Code is an AI coding assistant that helps developers write, review, and refactor code. It supports Python, JavaScript, and backend APIs.',
            chunk_size=180,
            start_position=0,
            end_position=180,
        )
        db.add(chunk)
        db.commit()
        db.refresh(chunk)

    vector_db = VectorDatabase()
    vector_db.add_chunk_to_vector_db(chunk, db)

    results = vector_db.search_relevant_chunks(
        query='What is Claude Code used for?',
        user_id=user.id,
        db=db,
        limit=3,
    )

    assert results, 'Expected relevant chunks to be found for the user document.'
    assert any('Claude Code' in item['content'] for item in results)
