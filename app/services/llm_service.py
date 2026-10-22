import os
from typing import List, Dict, Any

from dotenv import load_dotenv

load_dotenv()

try:
    from google import genai as google_genai
except ImportError:  # pragma: no cover
    google_genai = None

try:
    from groq import Groq
except ImportError:  # pragma: no cover
    Groq = None

SUPPORTED_GEMINI_MODELS = {
    "gemini-3.8-flash",
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
    "gemini-2.0-flash",
    "gemini-2.0-flash-lite",
}

SUPPORTED_GROQ_MODELS = {
    "openai/gpt-oss-20b",
    "openai/gpt-oss-120b",
    "meta-llama/llama-prompt-guard-2-22m",
    "qwen/qwen3.8-27b",
}


class LLMService:
    """Handle LLM interactions using Gemini or Groq."""

    def __init__(self):
        self.provider = os.getenv("LLM_PROVIDER", "groq").strip().lower()

        if self.provider == "groq":
            api_key = os.getenv("GROQ_API_KEY")
            if not api_key:
                raise ValueError("GROQ_API_KEY environment variable required")
            if Groq is None:
                raise ImportError("groq package is not installed. Install it with: pip install groq")
            self.client = Groq(api_key=api_key)
            configured_model = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")
            self.model_name = self._normalize_model_name(configured_model, "groq")
            self.provider_name = "groq"
            return

        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY environment variable required")
        if google_genai is None:
            raise ImportError("google-genai package is not installed")

        self.client = google_genai.Client(api_key=api_key)
        configured_model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        self.model_name = self._normalize_model_name(configured_model, "gemini")
        self.provider_name = "gemini"

    def _normalize_model_name(self, model_name: str, provider: str) -> str:
        """Ensure supported defaults for the selected provider."""
        normalized = (model_name or ("openai/gpt-oss-20b" if provider == "groq" else "gemini-2.5-flash")).strip()

        if provider == "groq":
            if normalized in SUPPORTED_GROQ_MODELS:
                return normalized
            return "openai/gpt-oss-20b"

        if normalized in SUPPORTED_GEMINI_MODELS:
            return normalized

        if normalized.startswith("gemini-"):
            for supported in ("gemini-2.5-flash", "gemini-2.0-flash"):
                if supported in SUPPORTED_GEMINI_MODELS:
                    return supported

        return "gemini-2.5-flash"

    def _extract_text(self, response: Any) -> str:
        """Extract text from a provider response."""
        if self.provider_name == "groq":
            if hasattr(response, "choices") and response.choices:
                message = response.choices[0].message
                if hasattr(message, "content"):
                    content = message.content
                    if isinstance(content, list):
                        parts = []
                        for item in content:
                            if isinstance(item, dict) and "text" in item:
                                parts.append(item["text"])
                        if parts:
                            return "".join(parts)
                    return str(content)
            return str(response)

        if hasattr(response, "text"):
            return response.text
        return str(response)

    def generate_rag_response(self, query: str, context: str, conversation_history: List[Dict] = None) -> str:
        """Generate response using the configured LLM provider."""

        prompt = f"""You are a helpful AI assistant that answers questions based on the provided context.

Context from documents:
{context}

Instructions:
- Answer the user's question using the provided context
- If the context doesn't contain relevant information, say so
- Be concise and helpful
- Cite which document sections you're referencing when possible

"""

        if conversation_history:
            prompt += "Previous conversation:\n"
            for msg in conversation_history[-4:]:
                role = "Human" if msg["role"] == "user" else "Assistant"
                prompt += f"{role}: {msg['content']}\n"
            prompt += "\n"

        prompt += f"Current question: {query}\n\nAnswer:"

        try:
            if self.provider_name == "groq":
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.2,
                    max_tokens=800,
                )
            else:
                response = self.client.models.generate_content(model=self.model_name, contents=prompt)

            text = self._extract_text(response)
            return text or "I'm having trouble generating a response right now."

        except Exception as e:
            error_text = str(e)
            print(f"LLM API error: {error_text}")

            if "403" in error_text or "PERMISSION_DENIED" in error_text or "API key" in error_text.lower():
                if self.provider_name == "groq":
                    return (
                        "The Groq API key is invalid, expired, or blocked. "
                        "Please update GROQ_API_KEY in your environment and restart the app."
                    )
                return (
                    "The Gemini API key is invalid, expired, or blocked. "
                    "Please update GOOGLE_API_KEY in your environment and restart the app."
                )

            return f"I'm having trouble generating a response right now. Error: {error_text}"

    def generate_conversation_title(self, first_message: str) -> str:
        """Generate a short title for the conversation."""
        try:
            prompt = f"Generate a short, descriptive title (max 5 words) for a conversation that starts with: '{first_message}'"
            if self.provider_name == "groq":
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.2,
                    max_tokens=30,
                )
            else:
                response = self.client.models.generate_content(model=self.model_name, contents=prompt)

            title = self._extract_text(response).strip().strip('"\'')
            return title[:50] or "New Conversation"

        except Exception:
            return "New Conversation"