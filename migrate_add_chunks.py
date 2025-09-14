import sys
sys.path.append('.')

from app.models.database import engine
from app.models import Base

def create_chunk_table():
    """Create the document_chunks table"""
    print("Creating document_chunks table...")
    Base.metadata.create_all(bind=engine)
    print("✅ Table created successfully!")

if __name__ == "__main__":
    create_chunk_table()