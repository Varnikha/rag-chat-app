# app/main.py - Complete with all routers

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = FastAPI(title="RAG Chat API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Check if environment variables are loaded
google_api_key = os.getenv("GOOGLE_API_KEY")
print(f"GOOGLE_API_KEY loaded: {'Yes' if google_api_key else 'No'}")
if google_api_key:
    print(f"API key starts with: {google_api_key[:10]}...")

# Import and create database tables
try:
    from app.models.database import create_tables
    
    @app.on_event("startup")
    async def startup_event():
        create_tables()
        print("Database tables created successfully!")
        
    database_status = "connected"
except Exception as e:
    print(f"Database error: {e}")
    database_status = f"error: {str(e)}"

# Import and include chat router
try:
    from app.routers.simple_chat import router as chat_router
    app.include_router(chat_router, prefix="/api/chat")
    chat_status = "connected"
    print("Chat router loaded successfully!")
except Exception as e:
    print(f"Chat router error: {e}")
    chat_status = f"error: {str(e)}"

# Import and include auth router
try:
    from app.routers.auth import router as auth_router
    app.include_router(auth_router, prefix="/api/auth")
    auth_status = "connected"
    print("Auth router loaded successfully!")
except Exception as e:
    print(f"Auth router error: {e}")
    auth_status = f"error: {str(e)}"

# Import and include documents router
try:
    from app.routers.documents import router as documents_router
    app.include_router(documents_router, prefix="/api/documents")
    documents_status = "connected"
    print("Documents router loaded successfully!")
except Exception as e:
    print(f"Documents router error: {e}")
    documents_status = f"error: {str(e)}"

@app.get("/")
async def root():
    return {
        "message": "RAG Chat API is running", 
        "step": "6 - Complete Backend with All Routers",
        "database": database_status,
        "chat": chat_status,
        "auth": auth_status,
        "documents": documents_status,
        "google_api_key_loaded": bool(google_api_key)
    }

@app.get("/health")
async def health():
    return {
        "status": "healthy", 
        "step": "6", 
        "database": database_status,
        "chat": chat_status,
        "auth": auth_status,
        "documents": documents_status,
        "google_api_key_loaded": bool(google_api_key)
    }