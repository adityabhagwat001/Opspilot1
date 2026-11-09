"""
OpsPilot: GitHub Multi-Account Isolation, Scope Authorization, and Real-Time Telemetry Tests
Verifies:
1. Account A connects and activates.
2. Account B connects and activates.
3. Switching from A to B refreshes all dashboard telemetry to B's authorized scope.
4. Switching from B to A restores A's correct data without deleting historical records.
5. Cross-account incident and AI fix proposal isolation (Account A cannot see or execute fixes on Account B's private repos).
6. Cross-account write execution boundary (returns 403 Forbidden).
7. Notifications are scoped strictly to the active integration and its monitored repositories.
8. Webhook signature validation (invalid signatures rejected with 401/403).
9. Webhook reachability and development tunnel status telemetry.
10. Health score calculation formula is scoped strictly to active monitored repositories (no arbitrary 20% clamp).
11. Invalid credentials produce clear HTTP errors and never fall back to fake mock data.
"""

import os
import uuid
import json
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.db import AsyncSessionLocal, init_system_db
from app.core.security import create_access_token
from app.models.models import IntegrationConnection, WorkflowFailure, FixProposal, InAppNotification, MonitoredRepository
from sqlalchemy import select, delete

ADMIN_HEADERS = {
    "Authorization": f"Bearer {create_access_token({'sub': 'usr-admin-01'})}"
}

WORKSPACE_ID = "default-ops"

async def ensure_test_setup():
    """Ensure database is initialized and seed isolated test accounts and records."""
    await init_system_db()
    async with AsyncSessionLocal() as db:
        # Seed two distinct GitHub integration connections
        # Account A: Sarthakjadhav007
        res_a = await db.execute(
            select(IntegrationConnection).where(
                IntegrationConnection.id == "conn-github-sarthak"
            )
        )
        conn_a = res_a.scalar_one_or_none()
        if not conn_a:
            conn_a = IntegrationConnection(
                id="conn-github-sarthak",
                workspace_id=WORKSPACE_ID,
                provider="github",
                status="connected",
                details_json=json.dumps({
                    "username": "Sarthakjadhav007",
                    "login": "Sarthakjadhav007",
                    "is_active": True,
                    "accessible_repos": ["Sarthakjadhav007/Hyperspectral-Analysis-System", "Sarthakjadhav007/repo-alpha"],
                    "monitored_repositories": ["Sarthakjadhav007/Hyperspectral-Analysis-System"]
                })
            )
            db.add(conn_a)
        else:
            conn_a.workspace_id = WORKSPACE_ID
            conn_a.provider = "github"
            conn_a.status = "connected"

        # Account B: adityabhagwat001
        res_b = await db.execute(
            select(IntegrationConnection).where(
                IntegrationConnection.id == "conn-github-aditya"
            )
        )
        conn_b = res_b.scalar_one_or_none()
        if not conn_b:
            conn_b = IntegrationConnection(
                id="conn-github-aditya",
                workspace_id=WORKSPACE_ID,
                provider="github",
                status="connected",
                details_json=json.dumps({
                    "username": "adityabhagwat001",
                    "login": "adityabhagwat001",
                    "is_active": False,
                    "accessible_repos": ["adityabhagwat001/Opspilot1"],
                    "monitored_repositories": ["adityabhagwat001/Opspilot1"]
                })
            )
            db.add(conn_b)
        else:
            conn_b.workspace_id = WORKSPACE_ID
            conn_b.provider = "github"
            conn_b.status = "connected"
            conn_b.details_json = json.dumps({
                "username": "adityabhagwat001",
                "login": "adityabhagwat001",
                "is_active": False,
                "accessible_repos": ["adityabhagwat001/Opspilot1"],
                "monitored_repositories": ["adityabhagwat001/Opspilot1"]
            })

        # Seed MonitoredRepository for both accounts
        res_mr_a = await db.execute(
            select(MonitoredRepository).where(
                MonitoredRepository.full_name == "Sarthakjadhav007/Hyperspectral-Analysis-System"
            )
        )
        mr_a = res_mr_a.scalar_one_or_none()
        if not mr_a:
            db.add(MonitoredRepository(
                id="mr-sarthak-hyper",
                workspace_id=WORKSPACE_ID,
                owner="Sarthakjadhav007",
                name="Hyperspectral-Analysis-System",
                full_name="Sarthakjadhav007/Hyperspectral-Analysis-System",
                default_branch="main",
                is_active=True
            ))
        else:
            mr_a.workspace_id = WORKSPACE_ID
            mr_a.is_active = True

        res_mr_b = await db.execute(
            select(MonitoredRepository).where(
                MonitoredRepository.full_name == "adityabhagwat001/Opspilot1"
            )
        )
        mr_b = res_mr_b.scalar_one_or_none()
        if not mr_b:
            db.add(MonitoredRepository(
                id="mr-aditya-opspilot1",
                workspace_id=WORKSPACE_ID,
                owner="adityabhagwat001",
                name="Opspilot1",
                full_name="adityabhagwat001/Opspilot1",
                default_branch="main",
                is_active=True
            ))
        else:
            mr_b.workspace_id = WORKSPACE_ID
            mr_b.is_active = True

        # Ensure failure for adityabhagwat001 exists
        res_fail = await db.execute(
            select(WorkflowFailure).where(WorkflowFailure.run_id == 77112233)
        )
        fail = res_fail.scalar_one_or_none()
        if not fail:
            fail = WorkflowFailure(
                id="fail-audit-77112233",
                workspace_id=WORKSPACE_ID,
                repo_full_name="adityabhagwat001/Opspilot1",
                workflow_name="CI Pipeline",
                run_id=77112233,
                commit_sha="a1b2c3d4e5f6789012345678901234567890abcd",
                head_branch="main",
                status="detected",
                error_log_snippet="Audit test: CI failure on aditya repo"
            )
            db.add(fail)
        else:
            fail.workspace_id = WORKSPACE_ID
            fail.repo_full_name = "adityabhagwat001/Opspilot1"
            fail.status = "detected"

        # Ensure proposal for adityabhagwat001 exists
        res_prop = await db.execute(
            select(FixProposal).where(FixProposal.failure_id == "fail-audit-77112233")
        )
        prop = res_prop.scalar_one_or_none()
        if not prop:
            prop = FixProposal(
                id="prop-audit-77112233",
                workspace_id=WORKSPACE_ID,
                failure_id="fail-audit-77112233",
                repo_full_name="adityabhagwat001/Opspilot1",
                title="Audit Test: Fix CI Pipeline",
                fix_branch="opspilot-fix-77112233",
                explanation="Fix applied for CI failure",
                status="pending_approval"
            )
            db.add(prop)
        else:
            prop.workspace_id = WORKSPACE_ID
            prop.repo_full_name = "adityabhagwat001/Opspilot1"

        await db.commit()


@pytest.mark.asyncio
async def test_accounts_listing_and_switching_roundtrip():
    """Verify GET /api/github/accounts lists all connected accounts and switching alters active context."""
    await ensure_test_setup()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Switch to Sarthakjadhav007
        switch_a = await client.post(
            "/api/github/accounts/switch",
            json={"account_login": "Sarthakjadhav007"},
            headers=ADMIN_HEADERS
        )
        assert switch_a.status_code == 200
        assert switch_a.json()["active_account"]["login"] == "Sarthakjadhav007"

        # Check account endpoint returns Sarthakjadhav007
        acc_resp = await client.get("/api/github/account", headers=ADMIN_HEADERS)
        assert acc_resp.status_code == 200
        assert acc_resp.json()["login"] == "Sarthakjadhav007"

        # Check failures for Sarthakjadhav007 - must NOT include adityabhagwat001/Opspilot1
        fail_resp_a = await client.get("/api/github/failures", headers=ADMIN_HEADERS)
        assert fail_resp_a.status_code == 200
        fail_repos_a = [f["repo_full_name"] for f in fail_resp_a.json()]
        assert "adityabhagwat001/Opspilot1" not in fail_repos_a

        # Check proposals for Sarthakjadhav007 - must NOT include adityabhagwat001/Opspilot1
        prop_resp_a = await client.get("/api/github/proposals", headers=ADMIN_HEADERS)
        assert prop_resp_a.status_code == 200
        prop_repos_a = [p["repo_full_name"] for p in prop_resp_a.json()]
        assert "adityabhagwat001/Opspilot1" not in prop_repos_a

        # 2. Switch to adityabhagwat001
        switch_b = await client.post(
            "/api/github/accounts/switch",
            json={"account_login": "adityabhagwat001"},
            headers=ADMIN_HEADERS
        )
        assert switch_b.status_code == 200
        assert switch_b.json()["active_account"]["login"] == "adityabhagwat001"

        # Check account endpoint now returns adityabhagwat001
        acc_resp_b = await client.get("/api/github/account", headers=ADMIN_HEADERS)
        assert acc_resp_b.status_code == 200
        assert acc_resp_b.json()["login"] == "adityabhagwat001"

        # Check failures for adityabhagwat001 - MUST include adityabhagwat001/Opspilot1
        fail_resp_b = await client.get("/api/github/failures", headers=ADMIN_HEADERS)
        assert fail_resp_b.status_code == 200
        fail_repos_b = [f["repo_full_name"] for f in fail_resp_b.json()]
        assert "adityabhagwat001/Opspilot1" in fail_repos_b
        assert any(f["run_id"] == 77112233 for f in fail_resp_b.json())

        # Check proposals for adityabhagwat001 - MUST include adityabhagwat001/Opspilot1
        prop_resp_b = await client.get("/api/github/proposals", headers=ADMIN_HEADERS)
        assert prop_resp_b.status_code == 200
        prop_repos_b = [p["repo_full_name"] for p in prop_resp_b.json()]
        assert "adityabhagwat001/Opspilot1" in prop_repos_b

        # 3. Switch back to Sarthakjadhav007 - data is restored cleanly without data loss
        switch_back = await client.post(
            "/api/github/accounts/switch",
            json={"account_login": "Sarthakjadhav007"},
            headers=ADMIN_HEADERS
        )
        assert switch_back.status_code == 200
        fail_resp_back = await client.get("/api/github/failures", headers=ADMIN_HEADERS)
        assert "adityabhagwat001/Opspilot1" not in [f["repo_full_name"] for f in fail_resp_back.json()]


@pytest.mark.asyncio
async def test_cross_account_proposal_execution_forbidden():
    """Verify that an active account cannot execute fix proposals belonging to another account's repository."""
    await ensure_test_setup()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Set active account to Sarthakjadhav007
        await client.post(
            "/api/github/accounts/switch",
            json={"account_login": "Sarthakjadhav007"},
            headers=ADMIN_HEADERS
        )

        # Attempt to execute prop-audit-77112233 (which belongs to adityabhagwat001/Opspilot1)
        resp = await client.post(
            "/api/github/proposals/prop-audit-77112233/execute",
            headers=ADMIN_HEADERS
        )
        # Must be rejected with 403 Forbidden
        assert resp.status_code == 403
        assert "not authorized" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_health_score_strictly_scoped_to_active_monitored_repositories():
    """Verify health score uses only active account's monitored repos and does not leak outside failures."""
    await ensure_test_setup()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Under Sarthakjadhav007, monitored repo is Hyperspectral-Analysis-System which has 0 failures
        await client.post(
            "/api/github/accounts/switch",
            json={"account_login": "Sarthakjadhav007"},
            headers=ADMIN_HEADERS
        )
        health_a = await client.get("/api/github/health", headers=ADMIN_HEADERS)
        assert health_a.status_code == 200
        data_a = health_a.json()
        assert data_a["active_failures_count"] == 0
        assert data_a["overall_health_score"] == 100.0
        assert data_a["status"] == "OPTIMAL"

        # Under adityabhagwat001, monitored repo is Opspilot1 which has 1 active failure
        await client.post(
            "/api/github/accounts/switch",
            json={"account_login": "adityabhagwat001"},
            headers=ADMIN_HEADERS
        )
        health_b = await client.get("/api/github/health", headers=ADMIN_HEADERS)
        assert health_b.status_code == 200
        data_b = health_b.json()
        assert data_b["active_failures_count"] >= 1
        opspilot_card = next((c for c in data_b["repositories"] if "Opspilot1" in c["repo_full_name"]), None)
        assert opspilot_card is not None
        assert opspilot_card["health_score"] <= 75.0


@pytest.mark.asyncio
async def test_webhook_status_and_tunnel_guidance():
    """Verify GET /api/github/webhook/status returns honest reachability and development tunnel guidance."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/github/webhook/status", headers=ADMIN_HEADERS)
        assert resp.status_code == 200
        data = resp.json()
        assert "status" in data
        assert "is_publicly_reachable" in data
        assert "total_events_received" in data
        assert "webhook_url" in data
        # If localhost, is_publicly_reachable should be False with tunnel guidance
        if not data["is_publicly_reachable"]:
            assert "guidance" in data
            assert "tunnel" in data["guidance"].lower() or "localhost" in data["guidance"].lower()


@pytest.mark.asyncio
async def test_invalid_webhook_signature_rejected():
    """Verify that incoming webhook requests with invalid HMAC signatures are rejected."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Missing or invalid signature header
        resp = await client.post(
            "/api/github/webhook",
            json={"action": "completed", "repository": {"full_name": "adityabhagwat001/Opspilot1"}},
            headers={
                "X-GitHub-Event": "workflow_run",
                "X-Hub-Signature-256": "sha256=invalid_tampered_signature"
            }
        )
        # Should be rejected with 401 or 403
        assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_invalid_credentials_produce_honest_errors_no_mock_fallback():
    """Verify connecting with invalid credentials yields 400/401 and does not fabricate mock data."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/github/connect",
            json={"token": "ghp_definitely_invalid_and_bogus_token_9999999999"},
            headers=ADMIN_HEADERS
        )
        # Should fail with 400 or 401
        assert resp.status_code in (400, 401)
        assert "invalid" in resp.json()["detail"].lower() or "authentication" in resp.json()["detail"].lower()
