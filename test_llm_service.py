import os

from app.services.llm_service import LLMService


def test_default_groq_model_is_supported(monkeypatch):
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.setenv("GROQ_API_KEY", "dummy-key")
    service = LLMService()
    assert service.provider_name == "groq"
    assert service.model_name == "llama-3.3-70b-versatile"


def test_default_gemini_model_is_supported(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    monkeypatch.setenv("GOOGLE_API_KEY", "dummy-key")
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    service = LLMService()
    assert service.provider_name == "gemini"
    assert service.model_name == "gemini-2.5-flash"
