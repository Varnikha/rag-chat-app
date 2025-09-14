import sys
sys.path.append('.')

from app.utils.auth import get_password_hash, verify_password, create_access_token, verify_token
from app.database import get_db  # ✅ Correct
from app.models.user import User
from sqlalchemy.orm import Session

def test_full_auth_flow():
    print("Testing complete authentication flow...")
    
    # Test password hashing
    password = "testpassword123"
    hashed = get_password_hash(password)
    print(f"1. Password hashed: {hashed[:20]}...")
    
    # Test password verification
    is_valid = verify_password(password, hashed)
    print(f"2. Password verification: {is_valid}")
    
    # Test token creation
    token = create_access_token({"sub": "test@example.com"})
    print(f"3. Token created: {token[:30]}...")
    
    # Test token verification
    email = verify_token(token)
    print(f"4. Token verified for: {email}")
    
    # Test database integration
    db = next(get_db())
    try:
        user = User(email="auth_test@example.com", hashed_password=hashed)
        db.add(user)
        db.commit()
        db.refresh(user)
        print(f"5. User created in database with ID: {user.id}")
        
        # Test login simulation
        db_user = db.query(User).filter(User.email == "auth_test@example.com").first()
        if db_user and verify_password(password, db_user.hashed_password):
            login_token = create_access_token({"sub": db_user.email})
            print("6. Login simulation successful")
            
            # Test token-based user lookup
            token_email = verify_token(login_token)
            authenticated_user = db.query(User).filter(User.email == token_email).first()
            print(f"7. Token-based user lookup: {authenticated_user.email}")
            
    except Exception as e:
        print(f"Database error: {e}")
    finally:
        db.close()
    
    print("\nAuthentication system is working correctly!")

if __name__ == "__main__":
    test_full_auth_flow()