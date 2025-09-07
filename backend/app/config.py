"""
Configuration settings for Partnership Tax Logic Engine
"""
from pydantic_settings import BaseSettings
from typing import List
import os

class Settings(BaseSettings):
    """Application settings"""
    
    # API Configuration
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Partnership Tax Logic Engine"
    VERSION: str = "1.0.0"
    
    # Database Configuration
    DATABASE_URL: str = "postgresql://user:password@localhost/partnership_tax_db"
    REDIS_URL: str = "redis://localhost:6379"
    
    # AI/ML Configuration
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    
    # Vector Database
    PINECONE_API_KEY: str = ""
    PINECONE_ENVIRONMENT: str = "us-west1-gcp"
    
    # Security
    SECRET_KEY: str = "your-secret-key-here"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # CORS
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:3001", 
        "http://127.0.0.1:3000",
        "https://app.partnership-tax-engine.com"
    ]
    
    # File Upload
    MAX_FILE_SIZE: int = 50 * 1024 * 1024  # 50MB
    ALLOWED_FILE_TYPES: List[str] = [".pdf", ".docx", ".doc"]
    
    # Processing Configuration
    DEFAULT_CONFIDENCE_THRESHOLD: float = 0.8
    MAX_CONCURRENT_PARSERS: int = 5
    
    # Logging
    LOG_LEVEL: str = "INFO"
    
    # External Integrations
    CCH_AXCESS_API_URL: str = ""
    CCH_AXCESS_API_KEY: str = ""
    
    THOMSON_REUTERS_API_URL: str = ""
    THOMSON_REUTERS_API_KEY: str = ""
    
    class Config:
        env_file = ".env"
        case_sensitive = True

# Create settings instance
settings = Settings()

# Development overrides
if os.getenv("ENVIRONMENT") == "development":
    settings.DATABASE_URL = "sqlite:///./partnership_tax_dev.db"
    settings.LOG_LEVEL = "DEBUG"