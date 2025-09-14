# app/routers/chat.py - FIXED VERSION
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List

# Import from database.py (don't redefine models here)
from app.database import get_db, User, ChatSession, ChatMessage
from app.routers.auth import get_current_user

router = APIRouter()

# Pydantic models for API
class ChatMessageCreate(BaseModel):
    content: str

class ChatMessageResponse(BaseModel):
    id: int
    content: str
    is_user_message: int
    timestamp: str
    
    class Config:
        from_attributes = True

class ChatSessionResponse(BaseModel):
    id: int
    created_at: str
    messages: List[ChatMessageResponse] = []
    
    class Config:
        from_attributes = True

# Routes
@router.get("/test")
async def test_chat():
    return {"message": "Chat router is working!", "status": "success"}

@router.post("/sessions", response_model=ChatSessionResponse)
async def create_chat_session(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new chat session"""
    session = ChatSession(user_id=current_user.id)
    db.add(session)
    db.commit()
    db.refresh(session)
    return session

@router.get("/sessions", response_model=List[ChatSessionResponse])
async def get_chat_sessions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all chat sessions for current user"""
    sessions = db.query(ChatSession).filter(ChatSession.user_id == current_user.id).all()
    return sessions

@router.post("/sessions/{session_id}/messages", response_model=ChatMessageResponse)
async def send_message(
    session_id: int,
    message: ChatMessageCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Send a message in a chat session"""
    # Verify session belongs to user
    session = db.query(ChatSession).filter(
        ChatSession.id == session_id,
        ChatSession.user_id == current_user.id
    ).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found")
    
    # Create user message
    user_message = ChatMessage(
        session_id=session_id,
        content=message.content,
        is_user_message=1
    )
    db.add(user_message)
    db.commit()
    db.refresh(user_message)
    
    # TODO: Add RAG processing here
    # For now, just echo back
    ai_response = f"I received your message: {message.content}"
    
    # Create AI response message
    ai_message = ChatMessage(
        session_id=session_id,
        content=ai_response,
        is_user_message=0
    )
    db.add(ai_message)
    db.commit()
    db.refresh(ai_message)
    
    return user_message

@router.get("/sessions/{session_id}/messages", response_model=List[ChatMessageResponse])
async def get_messages(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all messages in a chat session"""
    # Verify session belongs to user
    session = db.query(ChatSession).filter(
        ChatSession.id == session_id,
        ChatSession.user_id == current_user.id
    ).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found")
    
    messages = db.query(ChatMessage).filter(ChatMessage.session_id == session_id).all()
    return messages