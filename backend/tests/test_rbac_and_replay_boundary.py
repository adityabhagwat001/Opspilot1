"""
Security & Multi-Tenant Authorization Test Suite
Verifies:
1. Anonymous requests are strictly rejected with 401 (no admin fallback).
2. Inactive users are rejected with 401.
3. Viewer role is forbidden from approving writes (403).
4. Cross-workspace access is blocked (403/404).
5. Single-use tokens cannot be replayed (replay attack rejection).
6. Parameter tampering invalidates cryptographic tokens.
"""

import pytest
import datetime
import json
import uuid
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.db import AsyncSessionLocal, init_system_db
from app.core.security import (
    create_access_token,
    generate_approval_token,
    verify_approval_token,
    compute_action_hash
)
from app.models.models import User, Workspace, WorkspaceMember, ApprovalRequest, ConsumedApprovalToken
from app.approvals.approval_service import approval_service
from sqlalchemy import select

@pytest.mark.asyncio
async def test_anonymous_request_rejected_with_401():
    """Verify no anonymous fallback exists: missing Authorization header must return 401."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/dashboard/stats")
        assert resp.status_code == 401
        assert "Authentication token required" in resp.json().get("detail", "")

@pytest.mark.asyncio
async def test_inactive_user_rejected_with_401():
    """Verify deactivated user cannot make authenticated requests."""
    await init_system_db()
    user_id = f"usr-inactive-{uuid.uuid4().hex[:6]}"
    user_email = f"inactive-{uuid.uuid4().hex[:6]}@opspilot.internal"
    
    async with AsyncSessionLocal() as session:
        user = User(
            id=user_id,
            email=user_email,
            hashed_password="hash",
            full_name="Deactivated Operator",
            role="operator",
            is_active=False
        )
        session.add(user)
        await session.commit()

    token = create_access_token({"sub": user_id})
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/dashboard/stats", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 401
        assert "inactive" in resp.json().get("detail", "").lower()

@pytest.mark.asyncio
async def test_viewer_role_cannot_approve_write():
    """Verify viewer role receives 403 Forbidden when attempting to approve a write action."""
    await init_system_db()
    user_id = f"usr-viewer-{uuid.uuid4().hex[:6]}"
    user_email = f"viewer-{uuid.uuid4().hex[:6]}@opspilot.internal"
    
    async with AsyncSessionLocal() as session:
        viewer = User(
            id=user_id,
            email=user_email,
            hashed_password="hash",
            full_name="Read-Only Viewer",
            role="viewer",
            is_active=True
        )
        session.add(viewer)
        await session.commit()

    token = create_access_token({"sub": user_id})
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/approvals/non-existent-id/approve",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 403
        assert "Action requires one of the following roles" in resp.json().get("detail", "")

@pytest.mark.asyncio
async def test_cross_workspace_isolation():
    """Verify a user in workspace-A cannot access workspace-B objects."""
    await init_system_db()
    ws_id = f"ws-tenant-{uuid.uuid4().hex[:6]}"
    user_id = f"usr-tenant-{uuid.uuid4().hex[:6]}"
    user_email = f"operator-{uuid.uuid4().hex[:6]}@bravo.internal"
    
    async with AsyncSessionLocal() as session:
        ws_b = Workspace(id=ws_id, name="Bravo Tenant", slug=f"bravo-{uuid.uuid4().hex[:6]}")
        session.add(ws_b)

        user_b = User(
            id=user_id,
            email=user_email,
            hashed_password="hash",
            full_name="Bravo Operator",
            role="operator",
            is_active=True
        )
        session.add(user_b)
        session.add(WorkspaceMember(workspace_id=ws_id, user_id=user_id, role="operator"))
        await session.commit()

    token_b = create_access_token({"sub": user_id})
    
    # Try to access default-ops workspace as user Bravo
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get(
            "/api/dashboard/stats",
            headers={
                "Authorization": f"Bearer {token_b}",
                "X-Workspace-Id": "default-ops"
            }
        )
        assert resp.status_code == 403
        assert "not a member of workspace" in resp.json().get("detail", "")

@pytest.mark.asyncio
async def test_approval_nonce_replay_attack_blocked():
    """Verify approval token single-use enforcement: replaying a consumed nonce fails immediately."""
    consumed = set()
    tool_args = {"title": "Restart redis cluster", "priority": "p1"}
    
    token = generate_approval_token("create_operational_task", tool_args, nonce=f"nonce-{uuid.uuid4().hex[:8]}")
    
    # First use: passes and records nonce
    valid_1 = verify_approval_token("create_operational_task", tool_args, token, consumed_nonces=consumed)
    assert valid_1 is True

    # Second use (replay attack): fails
    valid_2 = verify_approval_token("create_operational_task", tool_args, token, consumed_nonces=consumed)
    assert valid_2 is False

@pytest.mark.asyncio
async def test_parameter_tampering_invalidates_token():
    """Verify that changing any parameter between approval and execution invalidates the grant."""
    original_args = {"recipient": "ops@enterprise.internal", "subject": "Notice", "body": "Clean update"}
    token = generate_approval_token("send_email", original_args)

    # Tampered recipient
    tampered_args_1 = {**original_args, "recipient": "attacker@external.bad"}
    assert verify_approval_token("send_email", tampered_args_1, token) is False

    # Tampered body
    tampered_args_2 = {**original_args, "body": "Malicious payload"}
    assert verify_approval_token("send_email", tampered_args_2, token) is False
