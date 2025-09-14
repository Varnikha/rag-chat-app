import os
from typing import List, Dict
import google.generativeai as genai

class LLMService:
    """Handle LLM interactions using Google Gemini"""
    
    def __init__(self):
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY environment variable required")
        
        genai.configure(api_key=api_key)
        # Use the correct model name for Gemini 1.5
        self.model = genai.GenerativeModel('gemini-1.5-flash')
    
    def generate_rag_response(self, query: str, context: str, conversation_history: List[Dict] = None) -> str:
        """Generate response using RAG context with Gemini"""
        
        # Build prompt
        prompt = f"""You are a helpful AI assistant that answers questions based on the provided context.

Context from documents:
{context}

Instructions:
- Answer the user's question using the provided context
- If the context doesn't contain relevant information, say so
- Be concise and helpful
- Cite which document sections you're referencing when possible

"""
        
        # Add conversation history if available
        if conversation_history:
            prompt += "Previous conversation:\n"
            for msg in conversation_history[-4:]:  # Last 4 messages
                role = "Human" if msg["role"] == "user" else "Assistant"
                prompt += f"{role}: {msg['content']}\n"
            prompt += "\n"
        
        # Add current question
        prompt += f"Current question: {query}\n\nAnswer:"
        
        try:
            response = self.model.generate_content(prompt)
            return response.text
        
        except Exception as e:
            print(f"Gemini API error: {e}")
            return f"I'm having trouble generating a response right now. Error: {str(e)}"
    
    def generate_conversation_title(self, first_message: str) -> str:
        """Generate a title for the conversation"""
        try:
            prompt = f"Generate a short, descriptive title (max 5 words) for a conversation that starts with: '{first_message}'"
            response = self.model.generate_content(prompt)
            title = response.text.strip().strip('"\'')
            return title[:50]  # Limit length
        
        except Exception as e:
            return "New Conversation"