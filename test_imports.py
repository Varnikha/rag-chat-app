# test_imports.py
try:
    print("Testing database import...")
    from app.database import Base, get_db
    print("✅ Database import successful")
    
    print("Testing User model import...")
    from app.models.user import User
    print("✅ User model import successful")
    
    print("Testing auth service import...")
    from app.services.auth_service import register_user
    print("✅ Auth service import successful")
    
    print("All imports working!")
    
except Exception as e:
    print(f"❌ Import error: {e}")