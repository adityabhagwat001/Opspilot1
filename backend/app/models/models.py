"""
OpsPilot Enterprise Database Models
SQLAlchemy ORM models covering RBAC, Executions, Approvals, and Audit Logs.
"""

import uuid
import datetime
from typing import Optional, List
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import String, Text, DateTime, Boolean, Integer, ForeignKey

class Base(DeclarativeBase):
    pass

def generate_uuid() -> str:
    return str(uuid.uuid4())

def utc_now() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)

class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(50), primary_key=True, default=generate_uuid)
    email: Mapped[str] = mapped_column(String(150), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(100), nullable=False)
    role: Mapped[str] = mapped_column(String(20), default="operator")  # admin, operator, viewer
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=utc_now)

class Workspace(Base):
    __tablename__ = "workspaces"

    id: Mapped[str] = mapped_column(String(50), primary_key=True, default=generate_uuid)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=utc_now)

class WorkspaceMember(Base):
    __tablename__ = "workspace_members"

    id: Mapped[str] = mapped_column(String(50), primary_key=True, default=generate_uuid)
    workspace_id: Mapped[str] = mapped_column(String(50), ForeignKey("workspaces.id"), nullable=False)
    user_id: Mapped[str] = mapped_column(String(50), ForeignKey("users.id"), nullable=False)
    role: Mapped[str] = mapped_column(String(20), default="operator")

class IntegrationConnection(Base):
    __tablename__ = "integration_connections"

    id: Mapped[str] = mapped_column(String(50), primary_key=True, default=generate_uuid)
    workspace_id: Mapped[str] = mapped_column(String(50), default="default-ops", index=True)
    provider: Mapped[str] = mapped_column(String(50), nullable=False)  # postgresql, github, email, calendar
    status: Mapped[str] = mapped_column(String(30), default="connected")  # connected, disconnected, error
    details_json: Mapped[str] = mapped_column(Text, default="{}")
    last_sync_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=utc_now)

class AgentConversation(Base):
    __tablename__ = "agent_conversations"

    id: Mapped[str] = mapped_column(String(50), primary_key=True, default=generate_uuid)
    workspace_id: Mapped[str] = mapped_column(String(50), default="default-ops", index=True)
    user_id: Mapped[str] = mapped_column(String(50), ForeignKey("users.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), default="Operational Session")
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=utc_now)
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=utc_now, onupdate=utc_now)

class AgentMessage(Base):
    __tablename__ = "agent_messages"

    id: Mapped[str] = mapped_column(String(50), primary_key=True, default=generate_uuid)
    conversation_id: Mapped[str] = mapped_column(String(50), ForeignKey("agent_conversations.id"), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)  # user, assistant, system
    content: Mapped[str] = mapped_column(Text, nullable=False)
    tool_calls_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tool_results_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=utc_now)

class AgentExecution(Base):
    __tablename__ = "agent_executions"

    id: Mapped[str] = mapped_column(String(50), primary_key=True, default=generate_uuid)
    conversation_id: Mapped[str] = mapped_column(String(50), ForeignKey("agent_conversations.id"), nullable=False)
    user_id: Mapped[str] = mapped_column(String(50), ForeignKey("users.id"), nullable=False)
    workspace_id: Mapped[str] = mapped_column(String(50), default="default-ops")
    user_request: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="received")  # received, running, awaiting_approval, completed, failed, rejected
    current_step: Mapped[str] = mapped_column(String(100), default="initialized")
    planned_actions_json: Mapped[str] = mapped_column(Text, default="[]")
    completed_actions_json: Mapped[str] = mapped_column(Text, default="[]")
    final_response: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=utc_now)
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=utc_now, onupdate=utc_now)

class ExecutionStep(Base):
    __tablename__ = "execution_steps"

    id: Mapped[str] = mapped_column(String(50), primary_key=True, default=generate_uuid)
    execution_id: Mapped[str] = mapped_column(String(50), ForeignKey("agent_executions.id"), nullable=False)
    step_index: Mapped[int] = mapped_column(Integer, nullable=False)
    step_name: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="started")  # started, completed, awaiting_approval, failed
    details_json: Mapped[str] = mapped_column(Text, default="{}")
    timestamp: Mapped[datetime.datetime] = mapped_column(DateTime, default=utc_now)

class ApprovalRequest(Base):
    __tablename__ = "approval_requests"

    id: Mapped[str] = mapped_column(String(50), primary_key=True, default=generate_uuid)
    execution_id: Mapped[str] = mapped_column(String(50), ForeignKey("agent_executions.id"), nullable=False)
    requesting_user_id: Mapped[str] = mapped_column(String(50), ForeignKey("users.id"), nullable=False)
    workspace_id: Mapped[str] = mapped_column(String(50), default="default-ops")
    target_system: Mapped[str] = mapped_column(String(50), nullable=False)  # postgresql, github, email, calendar
    tool_name: Mapped[str] = mapped_column(String(100), nullable=False)
    canonical_action_arguments: Mapped[str] = mapped_column(Text, nullable=False)  # JSON
    action_summary: Mapped[str] = mapped_column(Text, nullable=False)
    action_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    approval_status: Mapped[str] = mapped_column(String(30), default="pending")  # pending, approved, rejected, expired
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=utc_now)
    expires_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False)
    approved_by: Mapped[Optional[str]] = mapped_column(String(50), ForeignKey("users.id"), nullable=True)
    approved_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, nullable=True)
    execution_result: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(String(50), primary_key=True, default=generate_uuid)
    user_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    workspace_id: Mapped[str] = mapped_column(String(50), default="default-ops", index=True)
    action_type: Mapped[str] = mapped_column(String(50), nullable=False)  # READ_QUERY, WRITE_PROPOSED, APPROVAL_GRANTED, APPROVAL_REJECTED, WRITE_EXECUTED
    target_system: Mapped[str] = mapped_column(String(50), nullable=False)
    tool_name: Mapped[str] = mapped_column(String(100), nullable=False)
    parameters_json: Mapped[str] = mapped_column(Text, default="{}")
    approval_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    result_summary: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(20), default="success")  # success, failure, rejected
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=utc_now)
