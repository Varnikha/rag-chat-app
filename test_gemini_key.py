# test_gemini_key.py
# Quick test to check if your Google Gemini API key works

import os
from dotenv import load_dotenv
import google.generativeai as genai

# Load environment variables
load_dotenv()

def test_gemini_api():
    """Test if Google Gemini API key is working"""
    
    # Get API key
    api_key = os.getenv("GOOGLE_API_KEY")
    
    if not api_key:
        print("❌ ERROR: GOOGLE_API_KEY not found in environment variables")
        print("Check your .env file")
        return False
        
    print(f"✅ API Key found: {api_key[:10]}...")
    
    try:
        # Configure the API
        genai.configure(api_key=api_key)
        
        # Test with a simple prompt
        model = genai.GenerativeModel("gemini-1.5-flash")



        response = model.generate_content("Say hello and confirm you're working!")
        
        print("✅ SUCCESS! Google Gemini is working!")
        print(f"Response: {response.text}")
        return True
        
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        print("Possible issues:")
        print("- Invalid API key")
        print("- API key doesn't have proper permissions")
        print("- Network/firewall issues")
        return False

if __name__ == "__main__":
    print("Testing Google Gemini API Key...")
    print("-" * 40)
    test_gemini_api()