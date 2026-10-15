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
    workspace_id: Mapped[str] = mapped_column(String(50), default="default-ops", index=True)
    target_system: Mapped[str] = mapped_column(String(50), nullable=False)  # postgresql, github, email, calendar
    tool_name: Mapped[str] = mapped_column(String(100), nullable=False)
    target_resource: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    canonical_action_arguments: Mapped[str] = mapped_column(Text, nullable=False)  # JSON
    action_summary: Mapped[str] = mapped_column(Text, nullable=False)
    action_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    nonce: Mapped[Optional[str]] = mapped_column(String(64), unique=True, nullable=True, index=True)
    approval_status: Mapped[str] = mapped_column(String(30), default="pending", index=True)  # pending, executing, succeeded, failed, rejected, expired, superseded
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=utc_now)
    expires_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False)
    approved_by: Mapped[Optional[str]] = mapped_column(String(50), ForeignKey("users.id"), nullable=True)
    approved_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, nullable=True)
    execution_result: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON

class ConsumedApprovalToken(Base):
    __tablename__ = "consumed_approval_tokens"

    nonce: Mapped[str] = mapped_column(String(64), primary_key=True)
    approval_id: Mapped[str] = mapped_column(String(50), ForeignKey("approval_requests.id"), nullable=False)
    tool_name: Mapped[str] = mapped_column(String(100), nullable=False)
    workspace_id: Mapped[str] = mapped_column(String(50), nullable=False)
    action_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    consumed_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=utc_now)

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(String(50), primary_key=True, default=generate_uuid)
    user_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    workspace_id: Mapped[str] = mapped_column(String(50), default="default-ops", index=True)
    execution_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    correlation_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    action_type: Mapped[str] = mapped_column(String(50), nullable=False)  # READ_QUERY, WRITE_PROPOSED, APPROVAL_GRANTED, APPROVAL_REJECTED, WRITE_EXECUTED
    target_system: Mapped[str] = mapped_column(String(50), nullable=False)
    tool_name: Mapped[str] = mapped_column(String(100), nullable=False)
    parameters_json: Mapped[str] = mapped_column(Text, default="{}")
    approval_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    result_summary: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(20), default="success")  # success, failure, rejected
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=utc_now)

# =========================================================================
# GITHUB INTELLIGENCE & DEVOPS ADDITIVE MODELS
# =========================================================================

class MonitoredRepository(Base):
    __tablename__ = "monitored_repositories"

    id: Mapped[str] = mapped_column(String(50), primary_key=True, default=generate_uuid)
    workspace_id: Mapped[str] = mapped_column(String(50), default="default-ops", index=True)
    owner: Mapped[str] = mapped_column(String(100), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    full_name: Mapped[str] = mapped_column(String(200), unique=True, index=True, nullable=False)
    default_branch: Mapped[str] = mapped_column(String(50), default="main")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    health_score: Mapped[int] = mapped_column(Integer, default=100)
    last_sync_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=utc_now)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=utc_now)

    @property
    def is_monitored(self) -> bool:
        return self.is_active

    @is_monitored.setter
    def is_monitored(self, value: bool):
        self.is_active = value

    @property
    def repo_full_name(self) -> str:
        return self.full_name

    @repo_full_name.setter
    def repo_full_name(self, value: str):
        self.full_name = value

    @property
    def repo_name(self) -> str:
        return self.name

    @repo_name.setter
    def repo_name(self, value: str):
        self.name = value

    @property
    def last_synced_at(self) -> datetime.datetime:
        return self.last_sync_at

    @last_synced_at.setter
    def last_synced_at(self, value: datetime.datetime):
        self.last_sync_at = value

class GitHubEvent(Base):
    __tablename__ = "github_events"

    id: Mapped[str] = mapped_column(String(50), primary_key=True, default=generate_uuid)
    workspace_id: Mapped[str] = mapped_column(String(50), default="default-ops", index=True)
    delivery_id: Mapped[Optional[str]] = mapped_column(String(64), unique=True, nullable=True, index=True)
    repo_full_name: Mapped[str] = mapped_column(String(200), index=True, nullable=False)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # push, workflow_run, pull_request, issues
    action: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # completed, opened, synchronize
    actor: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    summary: Mapped[str] = mapped_column(String(255), nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=utc_now, index=True)

    @property
    def sender(self) -> Optional[str]:
        return self.actor

    @sender.setter
    def sender(self, value: Optional[str]):
        self.actor = value

class WorkflowFailure(Base):
    __tablename__ = "workflow_failures"

    id: Mapped[str] = mapped_column(String(50), primary_key=True, default=generate_uuid)
    workspace_id: Mapped[str] = mapped_column(String(50), default="default-ops", index=True)
    repo_full_name: Mapped[str] = mapped_column(String(200), index=True, nullable=False)
    run_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    workflow_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    workflow_name: Mapped[str] = mapped_column(String(150), nullable=False)
    event: Mapped[str] = mapped_column(String(50), default="push")
    head_branch: Mapped[str] = mapped_column(String(100), default="main")
    commit_sha: Mapped[str] = mapped_column(String(64), nullable=False)
    commit_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    actor: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    html_url: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    failing_step: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    error_log_snippet: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    analysis_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    root_cause: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="detected", index=True)  # detected, analyzing, fix_proposed, fix_approved, resolved
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=utc_now, index=True)

    @property
    def branch(self) -> str:
        return self.head_branch

    @branch.setter
    def branch(self, value: str):
        self.head_branch = value

    @property
    def sender(self) -> Optional[str]:
        return self.actor

    @sender.setter
    def sender(self, value: Optional[str]):
        self.actor = value

    @property
    def detected_at(self) -> datetime.datetime:
        return self.created_at

    @detected_at.setter
    def detected_at(self, value: datetime.datetime):
        self.created_at = value

class FixProposal(Base):
    __tablename__ = "fix_proposals"

    id: Mapped[str] = mapped_column(String(50), primary_key=True, default=generate_uuid)
    workspace_id: Mapped[str] = mapped_column(String(50), default="default-ops", index=True)
    failure_id: Mapped[Optional[str]] = mapped_column(String(50), ForeignKey("workflow_failures.id"), nullable=True)
    repo_full_name: Mapped[str] = mapped_column(String(200), index=True, nullable=False)
    target_branch: Mapped[str] = mapped_column(String(100), default="main")
    fix_branch: Mapped[str] = mapped_column(String(100), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    files_modified_json: Mapped[str] = mapped_column(Text, default="[]")  # list of {path, original, proposed, diff}
    diff: Mapped[str] = mapped_column(Text, default="")
    approval_id: Mapped[Optional[str]] = mapped_column(String(50), ForeignKey("approval_requests.id"), nullable=True)
    pull_request_url: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    pr_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="proposed", index=True)  # proposed, approved, executed, rejected, failed
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=utc_now)

    @property
    def branch_name(self) -> str:
        return self.fix_branch

    @branch_name.setter
    def branch_name(self, value: str):
        self.fix_branch = value

    @property
    def description(self) -> str:
        return self.explanation

    @description.setter
    def description(self, value: str):
        self.explanation = value

    @property
    def diff_content(self) -> str:
        return self.diff

    @diff_content.setter
    def diff_content(self, value: str):
        self.diff = value

    @property
    def files_changed_json(self) -> str:
        return self.files_modified_json

    @files_changed_json.setter
    def files_changed_json(self, value: str):
        self.files_modified_json = value

    @property
    def pr_url(self) -> Optional[str]:
        return self.pull_request_url

    @pr_url.setter
    def pr_url(self, value: Optional[str]):
        self.pull_request_url = value

class InAppNotification(Base):
    __tablename__ = "in_app_notifications"

    id: Mapped[str] = mapped_column(String(50), primary_key=True, default=generate_uuid)
    workspace_id: Mapped[str] = mapped_column(String(50), default="default-ops", index=True)
    user_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    title: Mapped[str] = mapped_column(String(150), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    level: Mapped[str] = mapped_column(String(20), default="info")  # info, warning, error, success
    category: Mapped[str] = mapped_column(String(30), default="github")  # github, approval, system
    link: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=utc_now, index=True)

    @property
    def notification_type(self) -> str:
        return self.category

    @notification_type.setter
    def notification_type(self, value: str):
        self.category = value

    @property
    def reference_id(self) -> Optional[str]:
        return self.link

    @reference_id.setter
    def reference_id(self, value: Optional[str]):
        self.link = value

