from sqlalchemy.orm import Session
from app.utils.auth import hash_password, verify_password, create_access_token
from app.database import Base

def register_user(db: Session, email: str, password: str):
    # Import locally to avoid circular import
    from app.models.user import User
    
    user = db.query(User).filter(User.email == email).first()
    if user:
        return None
    hashed_pw = hash_password(password)
    new_user = User(email=email, hashed_password=hashed_pw)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

def authenticate_user(db: Session, email: str, password: str):
    from app.models.user import User
    
    user = db.query(User).filter(User.email == email).first()
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user

def create_token_for_user(user):
    token_data = {"sub": user.email, "user_id": user.id}
    access_token = create_access_token(token_data)
    return access_token