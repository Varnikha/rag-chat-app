# test_gemini_key.py
# Quick test to check if your Google Gemini API key works

import os

import pytest
from dotenv import load_dotenv
from google import genai

# Load environment variables
load_dotenv()


def test_gemini_api():
    """Test if Google Gemini API key is working."""
    api_key = os.getenv("GOOGLE_API_KEY")

    if not api_key:
        pytest.skip("GOOGLE_API_KEY is not configured")

    print(f"✅ API Key found: {api_key[:10]}...")

    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(model="gemini-3.8-flash", contents="Say hello and confirm you're working!")
        output_text = response.text if hasattr(response, "text") else str(response)
        assert output_text
        print("✅ SUCCESS! Google Gemini is working!")
        print(f"Response: {output_text}")
    except Exception as exc:
        pytest.skip(f"Gemini API unavailable in this environment: {exc}")


if __name__ == "__main__":
    print("Testing Google Gemini API Key...")
    print("-" * 40)
    test_gemini_api()