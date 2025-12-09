from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    PROJECT_NAME: str = "Asian Paints RFP Orchestrator"
    
    # Supabase
    SUPABASE_URL: str
    SUPABASE_KEY: str
    
    # LLM (Cerebras / Groq)
    # If using Cerebras, Base URL might be https://api.cerebras.net/v1 or similar
    # If using Groq, Base URL might be https://api.groq.com/openai/v1
    LLM_BASE_URL: str = "https://api.cerebras.ai/v1" 
    LLM_API_KEY: str
    
    class Config:
        case_sensitive = True
        env_file = ".env"

settings = Settings()
