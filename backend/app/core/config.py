"""
OpsPilot Enterprise Configuration Settings
"""

import os
from typing import Optional
from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

# Automatically load .env file from project root
load_dotenv()

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=True, extra="allow")
    
    PROJECT_NAME: str = "OpsPilot Enterprise AI Platform"
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"
    
    # Security
    SECRET_KEY: str = "opspilot_super_secret_enterprise_jwt_key_change_in_production_32chars"
    APPROVAL_SECRET: str = "opspilot_trusted_approval_boundary_secret_key_32chars"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    APPROVAL_EXPIRE_MINUTES: int = 15  # 15 minutes window

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./opspilot_system.db"
    OPS_DATABASE_URL: str = "sqlite+aiosqlite:///./operational_data.db"

    # GitHub
    GITHUB_TOKEN: Optional[str] = ""
    GITHUB_DEFAULT_OWNER: Optional[str] = ""
    GITHUB_DEFAULT_REPO: Optional[str] = ""

    # LLM Settings
    LLM_PROVIDER: str = "openai"  # openai, anthropic, mock, ollama
    LLM_MODEL: str = "gpt-4o"
    OPENAI_API_KEY: Optional[str] = ""
    ANTHROPIC_API_KEY: Optional[str] = ""
    OPENROUTER_API_KEY: Optional[str] = ""

settings = Settings()

