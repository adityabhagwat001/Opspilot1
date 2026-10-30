"""
OpsPilot Pydantic Schemas for API Requests and Responses
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, EmailStr

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: Dict[str, Any]

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class ChatMessageRequest(BaseModel):
    conversation_id: Optional[str] = None
    message: str

class ApprovalDecisionRequest(BaseModel):
    reason: Optional[str] = None

class IntegrationStatusResponse(BaseModel):
    provider: str
    status: str
    name: str
    tool_count: int
    last_sync_at: Optional[str] = None

class GitHubConnectRequest(BaseModel):
    token: str
    username: Optional[str] = None
    default_repo: Optional[str] = None

