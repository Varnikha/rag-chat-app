import os
import sys
sys.path.append('.')

def test_models():
    print("Starting model test...")
    
    try:
        print("1. Importing modules...")
        from app.database import get_db,engine  # ✅ Correct
        from app.models.user import User
        from app.models.conversation import Conversation, Message  
        from app.models.document import Document
        from sqlalchemy.orm import Session
        print("   ✅ All imports successful")
        
        print("2. Creating database session...")
        db = Session(engine)
        print("   ✅ Database session created")
        
        print("3. Testing User model...")
        test_user = User(
            email="test@example.com",
            hashed_password="hashed_password_here"
        )
        db.add(test_user)
        db.commit()
        db.refresh(test_user)
        print(f"   ✅ User created with ID: {test_user.id}")
        
        print("4. Testing Conversation model...")
        test_conversation = Conversation(
            user_id=test_user.id,
            title="Test Conversation"
        )
        db.add(test_conversation)
        db.commit()
        db.refresh(test_conversation)
        print(f"   ✅ Conversation created with ID: {test_conversation.id}")
        
        print("5. Testing Message model...")
        test_message = Message(
            conversation_id=test_conversation.id,
            role="user",
            content="Hello, this is a test message!"
        )
        db.add(test_message)
        db.commit()
        db.refresh(test_message)
        print(f"   ✅ Message created with ID: {test_message.id}")
        
        print("6. Querying data back...")
        user_from_db = db.query(User).filter(User.email == "test@example.com").first()
        print(f"   ✅ Retrieved user: {user_from_db.email}")
        
        print("\n🎉 ALL TESTS PASSED! Your database models work correctly.")
        
    except Exception as e:
        print(f"❌ Error occurred: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        try:
            db.close()
            print("Database session closed.")
        except:
            pass

if __name__ == "__main__":
    test_models()