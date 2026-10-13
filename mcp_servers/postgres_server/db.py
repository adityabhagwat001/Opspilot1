"""
Operational Database Engine & Schema for OpsPilot PostgreSQL FastMCP Server.
Provides parameterized queries, connection pooling, and schema management.
Supports both PostgreSQL (asyncpg) and SQLite (aiosqlite) for zero-setup local resilience.
"""

import os
import datetime
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, Text, DateTime, ForeignKey, select, update, insert, func

# Resolve absolute path to operational_data.db in project root so queries work from any working directory
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DEFAULT_DB_FILE = os.path.join(PROJECT_ROOT, "operational_data.db").replace("\\", "/")
DEFAULT_DB_URL = os.getenv("OPS_DATABASE_URL", f"sqlite+aiosqlite:///{DEFAULT_DB_FILE}")

def utc_now() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)

class Base(DeclarativeBase):
    pass

class OperationalIncident(Base):
    __tablename__ = "operational_incidents"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)  # critical, high, medium, low
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="open")  # open, investigating, mitigated, resolved, closed
    service: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    assigned_to: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    workspace_id: Mapped[str] = mapped_column(String(50), default="default-ops", index=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=utc_now)
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=utc_now, onupdate=utc_now)

class OperationalTask(Base):
    __tablename__ = "operational_tasks"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    incident_id: Mapped[Optional[str]] = mapped_column(String(50), ForeignKey("operational_incidents.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="pending")  # pending, in_progress, completed, blocked
    priority: Mapped[str] = mapped_column(String(20), nullable=False, default="p1")  # p0, p1, p2, p3
    assignee: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    workspace_id: Mapped[str] = mapped_column(String(50), default="default-ops", index=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=utc_now)
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=utc_now, onupdate=utc_now)

class DatabaseEntity(Base):
    __tablename__ = "system_entities"

    name: Mapped[str] = mapped_column(String(100), primary_key=True)
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)  # table, view, microservice, cluster
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="healthy")  # healthy, degraded, offline
    region: Mapped[str] = mapped_column(String(50), default="us-east-1")
    description: Mapped[str] = mapped_column(Text, default="")
    record_count: Mapped[int] = mapped_column(default=0)
    workspace_id: Mapped[str] = mapped_column(String(50), default="default-ops", index=True)

class OperationsDatabase:
    def __init__(self, db_url: Optional[str] = None):
        self.db_url = db_url or DEFAULT_DB_URL
        self.engine = create_async_engine(self.db_url, echo=False)
        self.session_factory = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)

    async def init_db(self):
        """Create tables and seed initial operational baseline if empty."""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        # Seed baseline operations data if empty
        async with self.session_factory() as session:
            count = await session.scalar(select(func.count()).select_from(OperationalIncident))
            if count == 0:
                await self._seed_data(session)

    async def _seed_data(self, session: AsyncSession):
        incidents = [
            OperationalIncident(
                id="INC-101",
                title="Auth Service Latency Spike & Token Verification Timeout",
                severity="critical",
                status="open",
                service="auth-service",
                description="Token verification latency increased to 3500ms in us-east-1 causing cascading timeouts across API gateway.",
                assigned_to="aditya.b@enterprise.internal",
                workspace_id="default-ops",
                created_at=utc_now() - datetime.timedelta(hours=3),
                updated_at=utc_now() - datetime.timedelta(minutes=30),
            ),
            OperationalIncident(
                id="INC-102",
                title="Payment Webhook Gateway 504 Gateway Timeout",
                severity="high",
                status="investigating",
                service="payment-gateway",
                description="Intermittent 504 responses received when processing third-party webhook callbacks from Stripe provider.",
                assigned_to="ops-team@enterprise.internal",
                workspace_id="default-ops",
                created_at=utc_now() - datetime.timedelta(hours=8),
                updated_at=utc_now() - datetime.timedelta(hours=2),
            ),
            OperationalIncident(
                id="INC-103",
                title="Redis Cache Cluster Memory Pressure Warning (89% Capacity)",
                severity="medium",
                status="mitigated",
                service="cache-cluster",
                description="Cache eviction policy triggered in secondary Redis node; eviction buffer size adjusted.",
                assigned_to="infra-oncall@enterprise.internal",
                workspace_id="default-ops",
                created_at=utc_now() - datetime.timedelta(days=1),
                updated_at=utc_now() - datetime.timedelta(hours=6),
            ),
        ]
        session.add_all(incidents)

        tasks = [
            OperationalTask(
                id="TSK-301",
                incident_id="INC-101",
                title="Deploy hotfix for JWT verification connection pool exhaustion",
                description="Patch connection leak in auth-service database connection pool and verify response times under load.",
                status="in_progress",
                priority="p0",
                assignee="aditya.b@enterprise.internal",
                workspace_id="default-ops",
            ),
            OperationalTask(
                id="TSK-302",
                incident_id="INC-101",
                title="Increase auth-service read replica pool size to 50",
                description="Update terraform RDS connection limits for auth-service read replicas.",
                status="pending",
                priority="p1",
                assignee="devops@enterprise.internal",
                workspace_id="default-ops",
            ),
            OperationalTask(
                id="TSK-303",
                incident_id="INC-102",
                title="Implement exponential backoff retry queue for webhook handler",
                description="Route failed Stripe webhooks to dead-letter queue with exponential backoff retry policy.",
                status="pending",
                priority="p1",
                assignee="backend-eng@enterprise.internal",
                workspace_id="default-ops",
            ),
        ]
        session.add_all(tasks)

        entities = [
            DatabaseEntity(
                name="operational_incidents",
                entity_type="table",
                status="healthy",
                region="us-east-1",
                description="Live operational incident records and severity state machine",
                record_count=3,
                workspace_id="default-ops"
            ),
            DatabaseEntity(
                name="operational_tasks",
                entity_type="table",
                status="healthy",
                region="us-east-1",
                description="Remediation tasks and engineering action items linked to incidents",
                record_count=3,
                workspace_id="default-ops"
            ),
            DatabaseEntity(
                name="auth_sessions_replica",
                entity_type="table",
                status="degraded",
                region="us-east-1",
                description="PostgreSQL read replica for authentication sessions (high connection wait)",
                record_count=452000,
                workspace_id="default-ops"
            ),
            DatabaseEntity(
                name="redis_primary_cluster",
                entity_type="cache",
                status="healthy",
                region="us-east-1",
                description="Distributed session and rate limiting cache",
                record_count=1280000,
                workspace_id="default-ops"
            ),
        ]
        session.add_all(entities)
        await session.commit()

# Singleton instance
ops_db = OperationsDatabase()
