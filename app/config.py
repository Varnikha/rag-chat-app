import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./test.db")

# JWT Secret Key (generate a secure one for production)
SECRET_KEY = os.getenv("SECRET_KEY", "your-super-secret-jwt-key-change-this-in-production-12345")

# Google API
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# File upload settings
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
UPLOAD_DIR = "uploads"
ALLOWED_EXTENSIONS = {'.txt', '.pdf', '.docx', '.md'}

print("✅ Config loaded successfully!")