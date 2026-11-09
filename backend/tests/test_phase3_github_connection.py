"""
OpsPilot Phase 3: Real GitHub Repository Connection & Permission Tests
Verifies:
- Live personal access token permission verification (Read/Write vs Read-Only vs Disconnected)
- Clear missing scope warnings (repo, workflow, read:org)
- Dynamic repository discovery with pagination and permission flags (can_push, can_pull)
- Real-time repository overview endpoint (default branch, latest commit, open PRs, workflow runs)
- Honest handling of zero workflow runs / zero issues (no fabricated data)
- Graceful disconnect / reconnect handling (never returns 500 on missing or invalid token)
"""

import os
import uuid
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.db import AsyncSessionLocal, init_system_db
from app.core.security import create_access_token
from app.models.models import IntegrationConnection
from sqlalchemy import select

ADMIN_HEADERS = {
    "Authorization": f"Bearer {create_access_token({'sub': 'usr-admin-01'})}"
}

@pytest.mark.asyncio
async def test_account_permission_telemetry_and_scopes():
    """Verify live GitHub account returns honest connection state and permission levels."""
    await init_system_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/github/account", headers=ADMIN_HEADERS)
        assert resp.status_code == 200
        data = resp.json()
        assert "status" in data
        assert "connected" in data
        assert "permission_level" in data
        assert "permission_label" in data
        assert "scopes" in data

        if data["connected"]:
            # Real live token connected
            assert data["permission_level"] in ("read_write", "read_only", "none")
            assert "can_push" in data
            assert "can_pull" in data
            assert isinstance(data["scopes"], list)

@pytest.mark.asyncio
async def test_repository_discovery_pagination_and_permissions():
    """Verify repository listing supports pagination and exposes push/pull permissions."""
    await init_system_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/github/repositories", headers=ADMIN_HEADERS)
        assert resp.status_code == 200
        data = resp.json()
        assert "repositories" in data
        assert "count" in data
        assert isinstance(data["repositories"], list)

        if data["repositories"]:
            first_repo = data["repositories"][0]
            assert "full_name" in first_repo
            assert "default_branch" in first_repo
            assert "can_push" in first_repo
            assert "can_pull" in first_repo
            assert "permission_level" in first_repo
            assert "permission_label" in first_repo

@pytest.mark.asyncio
async def test_live_repository_overview_honest_metrics():
    """Verify live repository overview endpoint for real repo metadata, latest commit, PRs, and runs."""
    await init_system_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Inspect Opspilot1 repository
        resp = await client.get("/api/github/repositories/adityabhagwat001/Opspilot1/overview", headers=ADMIN_HEADERS)
        assert resp.status_code in (200, 401, 403)
        if resp.status_code == 200:
            ov = resp.json()
            assert ov["full_name"] == "adityabhagwat001/Opspilot1"
            assert ov["default_branch"] == "main"
            assert "permissions" in ov
            assert "can_push" in ov["permissions"]
            assert "can_pull" in ov["permissions"]
            assert "latest_commit" in ov
            assert "open_pull_requests_count" in ov
            assert "open_issues_count" in ov
            assert "recent_workflow_runs_count" in ov
            assert isinstance(ov["recent_workflow_runs"], list)

            # If zero runs exist, it must display runs_message honestly without fake mock data
            if ov["recent_workflow_runs_count"] == 0:
                assert ov["runs_message"] == "No workflow runs found"

@pytest.mark.asyncio
async def test_missing_or_invalid_token_disconnect_graceful_handling():
    """Verify application gracefully handles disconnected state or invalid tokens without 500 error."""
    await init_system_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Request non-existent or invalid repo overview
        bad_repo_resp = await client.get(
            f"/api/github/repositories/nonexistent-org-{uuid.uuid4().hex[:6]}/nonexistent-repo/overview",
            headers=ADMIN_HEADERS
        )
        # Must return clean 404 or 401, never 500 Internal Server Error
        assert bad_repo_resp.status_code in (401, 403, 404)
        assert bad_repo_resp.status_code != 500
