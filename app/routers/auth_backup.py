from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer
from pydantic import BaseModel
from sqlalchemy.orm import Session

# Import your existing functions
from app.services.auth_service import register_user, authenticate_user, create_token_for_user
from app.database import get_db
from app.utils.auth import verify_access_token

router = APIRouter(tags=["authentication"])
security = HTTPBearer()

class UserRegister(BaseModel):
    email: str
    password: str

class UserLogin(BaseModel):
    email: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class UserResponse(BaseModel):
    id: int
    email: str

@router.post("/register", response_model=Token)
async def register(user_data: UserRegister, db: Session = Depends(get_db)):
    try:
        user = register_user(db, user_data.email, user_data.password)
        if not user:
            raise HTTPException(status_code=400, detail="User already exists")
        
        token = create_token_for_user(user)
        return {"access_token": token, "token_type": "bearer"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/login", response_model=Token)
async def login(user_data: UserLogin, db: Session = Depends(get_db)):
    try:
        user = authenticate_user(db, user_data.email, user_data.password)
        if not user:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        token = create_token_for_user(user)
        return {"access_token": token, "token_type": "bearer"}
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid credentials")

@router.get("/me", response_model=UserResponse)
async def get_current_user(token: str = Depends(security), db: Session = Depends(get_db)):
    try:
        user = verify_access_token(token.credentials, db)
        if not user:
            raise HTTPException(status_code=401, detail="Invalid token")
        return {"id": user.id, "email": user.email}
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid token")