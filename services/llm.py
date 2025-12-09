from langchain_openai import ChatOpenAI
from app.core.config import settings

def get_llm():
    """
    Returns a configured ChatOpenAI instance pointing to the provider 
    (Cerebras, Groq, etc) as defined in .env
    """
    # Note: model name can be flexible. 
    # For Cerebras: "llama3.1-70b" or "llama3.1-8b"
    # For Groq: "llama-3.1-70b-versatile"
    # We default to a generic name, user might need to adjust in config or here.
    return ChatOpenAI(
        base_url=settings.LLM_BASE_URL,
        api_key=settings.LLM_API_KEY,
        model="llama3.1-70b", # Example default, check provider docs
        temperature=0.0
    )
