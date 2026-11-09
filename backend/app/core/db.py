"""
OpsPilot Core Database Initialization and Session Factory
"""

import json
import datetime
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select
from app.core.config import settings
from app.core.security import hash_password
from app.models.models import Base, User, Workspace, WorkspaceMember, IntegrationConnection

engine = create_async_engine(settings.DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

def configure_db_engine(db_url: str):
    global engine, AsyncSessionLocal
    engine = create_async_engine(db_url, echo=False)
    AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

async def init_system_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
        def _migrate(sync_conn):
            from sqlalchemy import text
            for tbl, col, typ in [
                ("approval_requests", "target_resource", "VARCHAR(255)"),
                ("approval_requests", "nonce", "VARCHAR(64)"),
                ("audit_logs", "execution_id", "VARCHAR(50)"),
                ("audit_logs", "correlation_id", "VARCHAR(64)"),
                ("workflow_failures", "root_cause", "TEXT"),
                ("workflow_failures", "workflow_id", "VARCHAR(50)"),
                ("workflow_failures", "html_url", "VARCHAR(255)"),
                ("fix_proposals", "pr_number", "INTEGER"),
                ("fix_proposals", "pr_state", "VARCHAR(30) DEFAULT 'NOT_CREATED'"),
                ("fix_proposals", "test_results_json", "TEXT"),
                ("fix_proposals", "resolution_status", "VARCHAR(30) DEFAULT 'NOT_VERIFIED'"),
                ("fix_proposals", "merge_commit_sha", "VARCHAR(64)"),
                ("fix_proposals", "merged_at", "DATETIME"),
                ("fix_proposals", "verified_at", "DATETIME"),
                ("fix_proposals", "verification_details_json", "TEXT"),
                ("workflow_failures", "analysis_status", "VARCHAR(30) DEFAULT 'NOT_ANALYZED'"),
                ("workflow_failures", "structured_analysis_json", "TEXT"),
                ("workflow_failures", "resolution_status", "VARCHAR(30) DEFAULT 'NOT_VERIFIED'"),
                ("workflow_failures", "resolution_evidence_json", "TEXT"),
                ("workflow_failures", "resolution_verified_at", "DATETIME"),
                ("audit_logs", "proposal_id", "VARCHAR(50)"),
                ("audit_logs", "failure_id", "VARCHAR(50)"),
                ("audit_logs", "repo_full_name", "VARCHAR(200)"),
                ("audit_logs", "solution_history_json", "TEXT"),
                ("in_app_notifications", "user_id", "VARCHAR(50)"),
                ("users", "is_verified", "BOOLEAN DEFAULT 0"),
                ("users", "verification_token", "VARCHAR(100)"),
                ("users", "verification_token_expires_at", "DATETIME"),
                ("users", "reset_password_token", "VARCHAR(100)"),
                ("users", "reset_password_token_expires_at", "DATETIME"),
                ("users", "account_type", "VARCHAR(20) DEFAULT 'individual'"),
                ("users", "account_status", "VARCHAR(30) DEFAULT 'active'"),
                ("users", "company_name", "VARCHAR(100)"),
                ("users", "last_login_at", "DATETIME"),
                ("users", "updated_at", "DATETIME"),
                ("workspaces", "company_email", "VARCHAR(150)"),
                ("workspaces", "website", "VARCHAR(255)"),
                ("workspaces", "industry", "VARCHAR(100)"),
                ("workspaces", "status", "VARCHAR(30) DEFAULT 'active'"),
                ("workspaces", "updated_at", "DATETIME"),
                ("workspace_invitations", "token_hash", "VARCHAR(64)")
            ]:
                try:
                    sync_conn.execute(text(f"ALTER TABLE {tbl} ADD COLUMN {col} {typ}"))
                except Exception:
                    pass
            try:
                sync_conn.execute(text("UPDATE users SET is_verified = 1 WHERE is_verified IS NULL OR email IN ('admin@opspilot.internal', 'operator@opspilot.internal')"))
                sync_conn.execute(text("UPDATE users SET account_status = 'active' WHERE account_status IS NULL"))
                sync_conn.execute(text("UPDATE workspaces SET status = 'active' WHERE status IS NULL"))
            except Exception:
                pass
        await conn.run_sync(_migrate)

    async with AsyncSessionLocal() as session:
        # Check if default workspace exists
        ws_stmt = select(Workspace).where(Workspace.id == "default-ops")
        ws = (await session.execute(ws_stmt)).scalar_one_or_none()
        if not ws:
            ws = Workspace(
                id="default-ops",
                name="Primary Operations Workspace",
                slug="primary-ops"
            )
            session.add(ws)

        # Check default admin user
        admin_stmt = select(User).where(User.email == "admin@opspilot.internal")
        admin = (await session.execute(admin_stmt)).scalar_one_or_none()
        if not admin:
            admin = User(
                id="usr-admin-01",
                email="admin@opspilot.internal",
                full_name="Enterprise Admin",
                hashed_password=hash_password("admin123"),
                role="admin",
                is_active=True,
                is_verified=True,
                account_type="individual"
            )
            session.add(admin)
        else:
            admin.is_verified = True

        # Check default operator user
        operator_stmt = select(User).where(User.email == "operator@opspilot.internal")
        operator = (await session.execute(operator_stmt)).scalar_one_or_none()
        if not operator:
            operator = User(
                id="usr-operator-01",
                email="operator@opspilot.internal",
                full_name="Lead DevOps Operator",
                hashed_password=hash_password("operator123"),
                role="operator",
                is_active=True,
                is_verified=True,
                account_type="individual"
            )
            session.add(operator)
        else:
            operator.is_verified = True

        # Ensure workspace memberships exist
        for u_id, u_role in [("usr-admin-01", "admin"), ("usr-operator-01", "operator")]:
            mem_stmt = select(WorkspaceMember).where(
                WorkspaceMember.workspace_id == "default-ops",
                WorkspaceMember.user_id == u_id
            )
            existing_mem = (await session.execute(mem_stmt)).scalar_one_or_none()
            if not existing_mem:
                session.add(WorkspaceMember(
                    workspace_id="default-ops",
                    user_id=u_id,
                    role=u_role
                ))

        # Ensure default connections are registered
        for provider, name in [
            ("postgresql", "PostgreSQL Operations DB (FastMCP)"),
            ("github", "GitHub Enterprise Integration (FastMCP)"),
            ("email", "Enterprise Mail Integration (FastMCP)"),
            ("calendar", "Enterprise Calendar Integration (FastMCP)")
        ]:
            conn_stmt = select(IntegrationConnection).where(
                IntegrationConnection.workspace_id == "default-ops",
                IntegrationConnection.provider == provider
            )
            existing = (await session.execute(conn_stmt)).scalars().first()
            if not existing:
                conn_rec = IntegrationConnection(
                    workspace_id="default-ops",
                    provider=provider,
                    status="connected",
                    details_json=json.dumps({"name": name, "verified_at": datetime.datetime.now(datetime.timezone.utc).isoformat() + "Z"})
                )
                session.add(conn_rec)

        await session.commit()
