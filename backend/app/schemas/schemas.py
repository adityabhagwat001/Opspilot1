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

class RegisterIndividualRequest(BaseModel):
    full_name: str
    email: EmailStr
    password: str
    confirm_password: str

class RegisterCompanyRequest(BaseModel):
    company_name: str
    company_email: Optional[EmailStr] = None
    company_website: Optional[str] = None
    industry: Optional[str] = None
    admin_full_name: str
    admin_email: EmailStr
    password: str
    confirm_password: str

class VerifyEmailRequest(BaseModel):
    token: str

class ResendVerificationRequest(BaseModel):
    email: EmailStr

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str
    confirm_password: str

class InviteEmployeeRequest(BaseModel):
    email: EmailStr
    role: Optional[str] = "operator"

class RegisterInviteRequest(BaseModel):
    token: str
    full_name: str
    password: str
    confirm_password: str

class UpdateMemberRoleRequest(BaseModel):
    role: str

class SwitchWorkspaceRequest(BaseModel):
    workspace_id: str

