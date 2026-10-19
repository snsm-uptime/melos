"""
Settings and configuration for Melos API
"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings from environment variables"""

    # Environment
    environment: str = "development"
    debug: bool = True
    log_level: str = "info"

    # Database
    database_url: str = "postgresql://melos:melos_dev_password@localhost:5432/melos_db"
    database_echo: bool = False

    # API
    api_title: str = "Melos API"
    api_version: str = "0.1.0"
    api_prefix: str = "/api/v1"

    # CORS
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:8000"]
    cors_allow_credentials: bool = True
    cors_allow_methods: list[str] = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    cors_allow_headers: list[str] = ["*"]

    # Session
    session_cookie_name: str = "melos_session"
    session_cookie_secure: bool = False  # Set to True in production
    session_cookie_httponly: bool = True
    session_cookie_samesite: str = "lax"
    session_expiry_hours: int = 24

    # Security
    password_min_length: int = 8
    password_max_length: int = 256
    secret_key: str = "dev-secret-key-change-in-production"

    # External Services
    gemini_api_key: Optional[str] = None
    gemini_model: str = "gemini-pro"
    gemini_vision_model: str = "gemini-pro-vision"
    gemini_embedding_model: str = "embedding-001"

    # Email (SMTP)
    smtp_host: str = "localhost"
    smtp_port: int = 1025
    smtp_user: Optional[str] = None
    smtp_password: Optional[str] = None
    smtp_from_email: str = "noreply@melos.local"

    # File Upload
    max_file_size_mb: int = 10
    allowed_image_extensions: list[str] = ["jpg", "jpeg", "png"]

    # Recipe Extraction
    recipe_extraction_timeout_seconds: int = 30
    page_fetch_timeout_seconds: int = 10

    # Embeddings
    pgvector_dimension: int = 768

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
