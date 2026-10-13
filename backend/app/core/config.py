"""
OpsPilot Enterprise Configuration Settings
"""

import os
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(case_sensitive=True, extra="allow")
    
    PROJECT_NAME: str = "OpsPilot Enterprise AI Platform"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "opspilot_super_secret_enterprise_jwt_key_change_in_production_32chars")
    APPROVAL_SECRET: str = os.getenv("OPSPILOT_APPROVAL_SECRET", "opspilot_trusted_approval_boundary_secret_key_32chars")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    APPROVAL_EXPIRE_MINUTES: int = 15  # 15 minutes window

    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./opspilot_system.db")
    OPS_DATABASE_URL: str = os.getenv("OPS_DATABASE_URL", "sqlite+aiosqlite:///./operational_data.db")

    # GitHub
    GITHUB_TOKEN: Optional[str] = os.getenv("GITHUB_TOKEN", "")
    GITHUB_DEFAULT_OWNER: Optional[str] = os.getenv("GITHUB_DEFAULT_OWNER", "")
    GITHUB_DEFAULT_REPO: Optional[str] = os.getenv("GITHUB_DEFAULT_REPO", "")

    # LLM Settings
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "openai")  # openai, anthropic, mock, ollama
    LLM_MODEL: str = os.getenv("LLM_MODEL", "gpt-4o")
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY", "")
    ANTHROPIC_API_KEY: Optional[str] = os.getenv("ANTHROPIC_API_KEY", "")
    OPENROUTER_API_KEY: Optional[str] = os.getenv("OPENROUTER_API_KEY", "")

settings = Settings()
