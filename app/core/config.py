import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    """Application settings"""
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://webhook_user:webhook_pass@localhost:5432/webhooks_db")
    DB_POOL_SIZE: int = int(os.getenv("DB_POOL_SIZE", "20"))
    DB_MAX_OVERFLOW: int = int(os.getenv("DB_MAX_OVERFLOW", "40"))
    
    # Redis
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    
    # Application
    APP_HOST: str = os.getenv("APP_HOST", "0.0.0.0")
    APP_PORT: int = int(os.getenv("APP_PORT", "5000"))
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    
    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "change-this-secret-key-in-production")
    
    # Google OAuth
    GOOGLE_CLIENT_ID: str = os.getenv("GOOGLE_CLIENT_ID", "")
    GOOGLE_CLIENT_SECRET: str = os.getenv("GOOGLE_CLIENT_SECRET", "")
    REDIRECT_URI: str = os.getenv("REDIRECT_URI", "http://localhost:5000/auth/callback")
    
    # Data Retention
    WEBHOOK_RETENTION_DAYS: int = int(os.getenv("WEBHOOK_RETENTION_DAYS", "30"))


settings = Settings()
