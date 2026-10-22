# app/routers/simple_chat.py - Step 5: Fixed method names

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session
from app.models.database import get_db

# RAG Integration - Fixed method names
try:
    from app.services.rag_service import RAGService
    from app.services.llm_service import LLMService
    
    # Initialize RAG services
    rag_service = RAGService()
    llm_service = LLMService()
    rag_available = True
    print("✅ RAG services loaded successfully!")
except Exception as e:
    print(f"⚠️ RAG services not available: {e}")
    rag_available = False

router = APIRouter(tags=["chat"])

class ChatMessage(BaseModel):
    message: str
    conversation_id: Optional[int] = None

class ChatResponse(BaseModel):
    response: str
    conversation_id: Optional[int] = None
    step: str

@router.post("/send", response_model=ChatResponse)
async def send_message(chat_message: ChatMessage, db: Session = Depends(get_db)):
    """Send a message - Simple version without RAG first"""
    try:
        response_text = f"Echo: {chat_message.message}"
        
        return ChatResponse(
            response=response_text,
            conversation_id=chat_message.conversation_id,
            step="3 - Simple Chat Working"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat error: {str(e)}")

@router.get("/test")
async def test_chat():
    """Test endpoint to verify chat router is working"""
    return {"status": "chat router working", "step": "3"}

@router.get("/simple-test/{message}")
async def simple_test(message: str):
    """Simple GET test that we can test in browser"""
    return {
        "your_message": message,
        "echo_response": f"Echo: {message}",
        "status": "working",
        "step": "3"
    }

# FIXED RAG ENDPOINT - Using correct method names
@router.post("/send-rag", response_model=ChatResponse)
async def send_message_with_rag(chat_message: ChatMessage, db: Session = Depends(get_db)):
    """Send a message with RAG integration"""
    try:
        if not rag_available:
            response_text = f"Simple Echo (RAG unavailable): {chat_message.message}"
        else:
            try:
                # Use the correct method from your RAG service
                # Assuming user_id = 1 for now (will fix with auth later)
                response_text = await rag_service.get_response(
                    query=chat_message.message, 
                    user_id=1  # Temporary user_id
                )
            except Exception as rag_error:
                print(f"RAG error: {rag_error}")
                response_text = f"RAG Error: {str(rag_error)}"
        
        return ChatResponse(
            response=response_text,
            conversation_id=chat_message.conversation_id,
            step="5 - Fixed RAG Integration"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"RAG Chat error: {str(e)}")

@router.get("/rag-status")
async def rag_status():
    """Check if RAG services are working"""
    return {
        "rag_available": rag_available,
        "step": "5",
        "status": "RAG integration fixed"
    }