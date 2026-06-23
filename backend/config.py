"""
LIFEOS Configuration — Settings & Environment Variables
"""
import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    """Application settings loaded from environment variables."""

    # API Keys
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")

    # MongoDB
    MONGODB_URI: str = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
    DATABASE_NAME: str = os.getenv("DATABASE_NAME", "lifeos")

    # App Config
    SECRET_KEY: str = os.getenv("SECRET_KEY", "lifeos-secret-key-change-me")
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:3000")

    # Groq Model
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama-3.1-70b-versatile")

    # LLM Settings
    LLM_TEMPERATURE: float = 0.7
    LLM_MAX_TOKENS: int = 4096

    # Agent Memory
    MEMORY_WINDOW_SIZE: int = 10  # Last N conversation turns to remember

    @property
    def is_development(self) -> bool:
        return self.ENVIRONMENT == "development"

    def validate(self) -> list[str]:
        """Check for missing required config. Returns list of warnings."""
        warnings = []
        if not self.GEMINI_API_KEY:
            warnings.append("GEMINI_API_KEY not set")
        if not self.GROQ_API_KEY:
            warnings.append("GROQ_API_KEY not set")
        if "localhost" in self.MONGODB_URI:
            warnings.append("MONGODB_URI using localhost — set Atlas URI for production")
        return warnings


settings = Settings()
