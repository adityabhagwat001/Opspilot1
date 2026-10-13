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

async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

async def init_system_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

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
                is_active=True
            )
            session.add(admin)

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
                is_active=True
            )
            session.add(operator)

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
            existing = (await session.execute(conn_stmt)).scalar_one_or_none()
            if not existing:
                conn_rec = IntegrationConnection(
                    workspace_id="default-ops",
                    provider=provider,
                    status="connected",
                    details_json=json.dumps({"name": name, "verified_at": datetime.datetime.now(datetime.timezone.utc).isoformat() + "Z"})
                )
                session.add(conn_rec)

        await session.commit()
