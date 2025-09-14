from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

from app.database import get_db
from app.models.user import Document, Conversation, Message
from app.services.rag_service import RAGService
from app.services.llm_service import LLMService

router = APIRouter(tags=["chat"])

class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[int] = None

class ChatResponse(BaseModel):
    response: str
    conversation_id: int
    message_id: int

class ConversationResponse(BaseModel):
    id: int
    title: str
    created_at: str
    message_count: int

# Initialize services
rag_service = RAGService()
llm_service = LLMService()

@router.post("/send", response_model=ChatResponse)
async def send_message(chat_request: ChatRequest, db: Session = Depends(get_db)):
    """Send a chat message and get RAG-powered AI response"""
    try:
        # Step 1: Get or create conversation
        conversation = None
        if chat_request.conversation_id:
            conversation = db.query(Conversation).filter(
                Conversation.id == chat_request.conversation_id
            ).first()
        
        if not conversation:
            # Create new conversation
            conversation = Conversation(
                user_id=1,  # TODO: Get from JWT token
                title=chat_request.message[:50] + "..." if len(chat_request.message) > 50 else chat_request.message,
                created_at=datetime.utcnow()
            )
            db.add(conversation)
            db.commit()
            db.refresh(conversation)

        # Step 2: Save user message to database
        user_message = Message(
            conversation_id=conversation.id,
            role="user",
            content=chat_request.message,
            timestamp=datetime.utcnow()
        )
        db.add(user_message)
        db.commit()
        db.refresh(user_message)

        # Step 3: Get user's documents for RAG context
        user_documents = db.query(Document).filter(
            Document.user_id == 1,  # TODO: Get from JWT token
            Document.processed == True
        ).all()

        if not user_documents:
            # No documents uploaded yet
            ai_response = "I don't have any documents to reference. Please upload some documents first so I can help answer questions about them."
        else:
            # Step 4: Use RAG service to get relevant context
            relevant_context = await rag_service.search_documents(
                query=chat_request.message,
                user_id=1  # TODO: Get from JWT token
            )

            # Step 5: Generate AI response using LLM service
            ai_response = await llm_service.generate_response(
                query=chat_request.message,
                context=relevant_context
            )

        # Step 6: Save AI response to database
        ai_message = Message(
            conversation_id=conversation.id,
            role="assistant", 
            content=ai_response,
            timestamp=datetime.utcnow()
        )
        db.add(ai_message)
        db.commit()
        db.refresh(ai_message)

        return {
            "response": ai_response,
            "conversation_id": conversation.id,
            "message_id": ai_message.id
        }

    except Exception as e:
        print(f"Chat error: {e}")  # For debugging
        raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}")

@router.get("/conversations", response_model=List[ConversationResponse])
async def get_conversations(db: Session = Depends(get_db)):
    """Get user's conversation history"""
    try:
        conversations = db.query(Conversation).filter(
            Conversation.user_id == 1  # TODO: Get from JWT token
        ).order_by(Conversation.created_at.desc()).all()

        return [
            {
                "id": conv.id,
                "title": conv.title,
                "created_at": conv.created_at.isoformat(),
                "message_count": len(conv.messages) if hasattr(conv, 'messages') else 0
            }
            for conv in conversations
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get conversations: {str(e)}")

@router.get("/conversations/{conversation_id}/messages")
async def get_conversation_messages(conversation_id: int, db: Session = Depends(get_db)):
    """Get messages from a specific conversation"""
    try:
        conversation = db.query(Conversation).filter(
            Conversation.id == conversation_id,
            Conversation.user_id == 1  # TODO: Get from JWT token
        ).first()

        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")

        messages = db.query(Message).filter(
            Message.conversation_id == conversation_id
        ).order_by(Message.timestamp.asc()).all()

        return {
            "conversation_id": conversation_id,
            "messages": [
                {
                    "id": msg.id,
                    "role": msg.role,
                    "content": msg.content,
                    "timestamp": msg.timestamp.isoformat()
                }
                for msg in messages
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get messages: {str(e)}")