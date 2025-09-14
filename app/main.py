# app/main.py - COMPLETE VERSION WITH ALL SUCCESS MESSAGES
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import database
from app.database import create_tables

# Create FastAPI app
app = FastAPI(title="RAG Chat API", version="1.0.0")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database
try:
    create_tables()
    print("✅ Database tables created successfully!")
except Exception as e:
    print(f"❌ Database error: {e}")

# Load config
try:
    from app.config import SECRET_KEY
    print("✅ Config loaded successfully!")
except Exception as e:
    print(f"❌ Config error: {e}")

# Import and register auth router
try:
    from app.routers.auth import router as auth_router
    print("✅ Auth router imported successfully!")
    app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
    print("✅ Auth router registered!")
except Exception as e:
    print(f"❌ Auth router error: {e}")

# Import and register documents router
try:
    from app.routers.documents import router as documents_router
    print("✅ Documents router imported successfully!")
    app.include_router(documents_router, prefix="/api/documents", tags=["documents"])
    print("✅ Documents router registered!")
except Exception as e:
    print(f"❌ Documents router error: {e}")

# Import and register chat router
try:
    from app.routers.chat import router as chat_router
    print("✅ Chat router imported successfully!")
    app.include_router(chat_router, prefix="/api/chat", tags=["chat"])
    print("✅ Chat router registered!")
except Exception as e:
    print(f"❌ Chat router error: {e}")

# Import RAG service
try:
    from app.services.rag_service import RAGService
    rag_service = RAGService()
    print("✅ RAG service imported successfully!")
    print("✅ RAG service initialized successfully!")
except Exception as e:
    print(f"❌ RAG service error: {e}")

@app.get("/")
async def root():
    return {"message": "RAG Chat API is running!", "status": "success"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)