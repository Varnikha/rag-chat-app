# app/routers/chat.py - FIXED VERSION
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List

from app.database import get_db, User, Conversation, Message, Document
from app.models.chunk import DocumentChunk
from app.services.llm_service import LLMService
from app.services.vector_database import VectorDatabase
from app.routers.auth import get_current_user

router = APIRouter()


class ChatMessageCreate(BaseModel):
    content: str


class ChatMessageResponse(BaseModel):
    id: int
    role: str
    content: str
    timestamp: datetime

    class Config:
        from_attributes = True


class ChatSessionResponse(BaseModel):
    id: int
    title: str
    created_at: datetime
    messages: List[ChatMessageResponse] = []

    class Config:
        from_attributes = True


@router.get("/test")
async def test_chat():
    return {"message": "Chat router is working!", "status": "success"}


@router.post("/sessions", response_model=ChatSessionResponse)
async def create_chat_session(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new chat session."""
    session = Conversation(
        user_id=current_user.id,
        title=f"Chat - {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}"
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


@router.get("/sessions", response_model=List[ChatSessionResponse])
async def get_chat_sessions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get all chat sessions for current user."""
    sessions = db.query(Conversation).filter(Conversation.user_id == current_user.id).all()
    return sessions


@router.post("/sessions/{session_id}/messages", response_model=ChatMessageResponse)
async def send_message(
    session_id: int,
    message: ChatMessageCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Send a message in a chat session and generate a grounded assistant reply."""
    session = db.query(Conversation).filter(
        Conversation.id == session_id,
        Conversation.user_id == current_user.id,
    ).first()

    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found")

    user_message = Message(
        conversation_id=session_id,
        role="user",
        content=message.content,
    )
    db.add(user_message)
    db.commit()
    db.refresh(user_message)

    try:
        llm_service = LLMService()
    except Exception:
        llm_service = None

    relevant_chunks = []
    try:
        vector_db = VectorDatabase()
        relevant_chunks = vector_db.search_relevant_chunks(
            query=message.content,
            user_id=current_user.id,
            db=db,
            limit=5,
        )
    except Exception as exc:
        print(f"Vector retrieval failed: {exc}")
        relevant_chunks = []

    if not relevant_chunks:
        db_chunks = (
            db.query(DocumentChunk)
            .join(Document, Document.id == DocumentChunk.document_id)
            .filter(Document.user_id == current_user.id)
            .order_by(DocumentChunk.chunk_index)
            .limit(5)
            .all()
        )
        relevant_chunks = [{"content": chunk.content} for chunk in db_chunks]

    context = "\n\n".join(
        item.get("content", "") for item in relevant_chunks if item.get("content")
    )

    history = (
        db.query(Message)
        .filter(Message.conversation_id == session_id)
        .order_by(Message.id)
        .all()
    )
    conversation_history = [
        {"role": msg.role, "content": msg.content} for msg in history[-4:]
    ]

    if llm_service and context:
        ai_response = llm_service.generate_rag_response(
            query=message.content,
            context=context,
            conversation_history=conversation_history,
        )
    elif llm_service:
        ai_response = (
            "I couldn’t find relevant resume context for that question, "
            "so I can only answer from general knowledge."
        )
    else:
        ai_response = (
            "The LLM service is not configured, so I can’t generate a real answer yet."
        )

    ai_message = Message(
        conversation_id=session_id,
        role="assistant",
        content=ai_response,
    )
    db.add(ai_message)
    db.commit()
    db.refresh(ai_message)

    return ai_message


@router.get("/sessions/{session_id}/messages", response_model=List[ChatMessageResponse])
async def get_messages(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get all messages in a chat session."""
    session = db.query(Conversation).filter(
        Conversation.id == session_id,
        Conversation.user_id == current_user.id,
    ).first()

    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found")

    messages = db.query(Message).filter(Message.conversation_id == session_id).all()
    return messages