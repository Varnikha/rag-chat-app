from datetime import datetime
import os
import sqlite3

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text, create_engine
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

# Database setup
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./rag_chat.db")

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=True)
    email = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    documents = relationship("Document", back_populates="user")
    conversations = relationship("Conversation", back_populates="user")


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=True)
    file_size = Column(Integer, nullable=False, default=0)
    content = Column(Text, nullable=True)
    content_preview = Column(Text, nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    processed = Column(Boolean, default=False, nullable=False)

    user = relationship("User", back_populates="documents")


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False)
    role = Column(String(50), nullable=False)
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)

    conversation = relationship("Conversation", back_populates="messages")


# Backward-compatible aliases for older imports
ChatSession = Conversation
ChatMessage = Message


def migrate_legacy_user_schema():
    if "sqlite" not in DATABASE_URL:
        return

    db_path = DATABASE_URL.replace("sqlite:///", "")
    if db_path.startswith("./"):
        db_path = db_path[2:]

    if not os.path.exists(db_path):
        return

    with engine.begin() as conn:
        columns = conn.exec_driver_sql("PRAGMA table_info(users)").fetchall()
        names = {column[1] for column in columns}

        if not columns or "hashed_password" in names:
            return

        if "password" not in names:
            return

        stale_indexes = conn.exec_driver_sql(
            "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='users'"
        ).fetchall()
        for (index_name,) in stale_indexes:
            conn.exec_driver_sql(f"DROP INDEX IF EXISTS {index_name}")

        conn.exec_driver_sql("ALTER TABLE users RENAME TO users_legacy")
        User.__table__.create(bind=conn)
        conn.exec_driver_sql(
            "INSERT INTO users (id, username, email, hashed_password, created_at) "
            "SELECT id, username, email, password, created_at FROM users_legacy"
        )
        conn.exec_driver_sql("DROP TABLE users_legacy")


def migrate_legacy_document_schema():
    if "sqlite" not in DATABASE_URL:
        return

    db_path = DATABASE_URL.replace("sqlite:///", "")
    if db_path.startswith("./"):
        db_path = db_path[2:]

    if not os.path.exists(db_path):
        return

    with engine.begin() as conn:
        columns = conn.exec_driver_sql("PRAGMA table_info(documents)").fetchall()
        if not columns:
            return

        present = {column[1] for column in columns}
        required = {"file_path", "file_size", "content_preview", "processed"}
        if required.issubset(present):
            return

        conn.exec_driver_sql("ALTER TABLE documents RENAME TO documents_legacy")
        Document.__table__.create(bind=conn)
        conn.exec_driver_sql(
            "INSERT INTO documents (id, filename, file_path, file_size, content, content_preview, user_id, uploaded_at, processed) "
            "SELECT id, filename, '', LENGTH(content), content, substr(content, 1, 500), user_id, uploaded_at, 1 FROM documents_legacy"
        )
        conn.exec_driver_sql("DROP TABLE documents_legacy")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables():
    try:
        migrate_legacy_user_schema()
        migrate_legacy_document_schema()
        Base.metadata.create_all(bind=engine)
        print("✅ Database tables created successfully!")
    except Exception as e:
        print(f"❌ Error creating database tables: {e}")


if __name__ == "__main__":
    create_tables()