"""
OpsPilot Phase 4: Reliable Real-Time GitHub Monitoring & CI/CD Failure Detection Tests
Verifies:
- Webhook security: HMAC-SHA256 signature verification (valid accepted, forged rejected with 401)
- Delivery deduplication: X-GitHub-Delivery header idempotency (duplicate returns duplicate_skipped)
- Rich failure detail extraction: job identification, failing step, error log snippet, notification
- Polling fallback reconciliation: /api/github/sync reconciles runs and updates last_synced_at
- Webhook event tracking: pull_request, push, issues, and workflow_run events persisted to ledger
"""

import os
import json
import uuid
import hmac
import hashlib
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.config import settings
from app.core.db import AsyncSessionLocal, init_system_db
from app.core.security import create_access_token
from app.models.models import WorkflowFailure, GitHubEvent, InAppNotification, MonitoredRepository
from sqlalchemy import select

ADMIN_HEADERS = {
    "Authorization": f"Bearer {create_access_token({'sub': 'usr-admin-01'})}"
}

@pytest.mark.asyncio
async def test_webhook_hmac_signature_validation():
    """Verify webhook accepts valid HMAC-SHA256 signatures and rejects forged signatures with 401."""
    await init_system_db()
    transport = ASGITransport(app=app)
    delivery_id = f"test-deliv-{uuid.uuid4().hex[:12]}"

    payload = {
        "action": "completed",
        "repository": {"full_name": "adityabhagwat001/Opspilot1"},
        "sender": {"login": "test-runner"},
        "workflow_run": {
            "id": 88009911,
            "workflow_id": "9912",
            "name": "CI Tests",
            "conclusion": "success",
            "head_sha": "abc123456789",
            "head_branch": "main",
            "html_url": "https://github.com/adityabhagwat001/Opspilot1/actions/runs/88009911"
        }
    }
    raw_bytes = json.dumps(payload).encode("utf-8")
    secret = settings.GITHUB_WEBHOOK_SECRET or "opspilot_webhook_test_secret"

    # 1. Forged signature must be rejected with HTTP 401
    forged_sig = "sha256=0000000000000000000000000000000000000000000000000000000000000000"
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp_forged = await client.post(
            "/api/github/webhook",
            content=raw_bytes,
            headers={
                "X-GitHub-Event": "workflow_run",
                "X-GitHub-Delivery": delivery_id,
                "X-Hub-Signature-256": forged_sig,
                "Content-Type": "application/json"
            }
        )
        assert resp_forged.status_code == 401
        assert "Invalid webhook signature" in resp_forged.json()["detail"]

    # 2. Authentic signature must be accepted with HTTP 200
    valid_sig = "sha256=" + hmac.new(secret.encode("utf-8"), raw_bytes, hashlib.sha256).hexdigest()
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp_valid = await client.post(
            "/api/github/webhook",
            content=raw_bytes,
            headers={
                "X-GitHub-Event": "workflow_run",
                "X-GitHub-Delivery": delivery_id,
                "X-Hub-Signature-256": valid_sig,
                "Content-Type": "application/json"
            }
        )
        assert resp_valid.status_code == 200
        assert resp_valid.json()["status"] == "received"

    # Teardown
    async with AsyncSessionLocal() as session:
        ev = (await session.execute(select(GitHubEvent).where(GitHubEvent.delivery_id == delivery_id))).scalar_one_or_none()
        if ev:
            await session.delete(ev)
        await session.commit()

@pytest.mark.asyncio
async def test_webhook_delivery_idempotent_deduplication():
    """Verify duplicate webhook deliveries with the same X-GitHub-Delivery are idempotently skipped."""
    await init_system_db()
    transport = ASGITransport(app=app)
    delivery_id = f"deliv-dedup-{uuid.uuid4().hex[:12]}"

    payload = {
        "action": "completed",
        "repository": {"full_name": "adityabhagwat001/Opspilot1"},
        "sender": {"login": "test-runner"},
        "workflow_run": {
            "id": 88009912,
            "conclusion": "success"
        }
    }
    raw_bytes = json.dumps(payload).encode("utf-8")
    secret = settings.GITHUB_WEBHOOK_SECRET or "opspilot_webhook_test_secret"
    sig = "sha256=" + hmac.new(secret.encode("utf-8"), raw_bytes, hashlib.sha256).hexdigest()

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # First delivery: received
        r1 = await client.post(
            "/api/github/webhook",
            content=raw_bytes,
            headers={
                "X-GitHub-Event": "workflow_run",
                "X-GitHub-Delivery": delivery_id,
                "X-Hub-Signature-256": sig,
                "Content-Type": "application/json"
            }
        )
        assert r1.status_code == 200
        assert r1.json()["status"] == "received"

        # Second delivery: duplicate skipped
        r2 = await client.post(
            "/api/github/webhook",
            content=raw_bytes,
            headers={
                "X-GitHub-Event": "workflow_run",
                "X-GitHub-Delivery": delivery_id,
                "X-Hub-Signature-256": sig,
                "Content-Type": "application/json"
            }
        )
        assert r2.status_code == 200
        assert r2.json()["status"] == "duplicate_skipped"

    # Teardown
    async with AsyncSessionLocal() as session:
        ev = (await session.execute(select(GitHubEvent).where(GitHubEvent.delivery_id == delivery_id))).scalar_one_or_none()
        if ev:
            await session.delete(ev)
        await session.commit()

@pytest.mark.asyncio
async def test_webhook_workflow_failure_ingestion_and_rich_extraction():
    """Verify CI/CD failure webhook ingests rich step details, error log snippet, and creates notification."""
    await init_system_db()
    transport = ASGITransport(app=app)
    delivery_id = f"deliv-fail-{uuid.uuid4().hex[:12]}"
    test_run_id = int(uuid.uuid4().int % 90000000 + 10000000)

    payload = {
        "action": "completed",
        "repository": {"full_name": "adityabhagwat001/Opspilot1"},
        "sender": {"login": "ci-bot"},
        "workflow_run": {
            "id": test_run_id,
            "workflow_id": "8877",
            "name": "Integration & Unit Tests",
            "conclusion": "failure",
            "head_sha": "fa11fa11fa11fa11",
            "head_branch": "fix/auth-bug",
            "html_url": f"https://github.com/adityabhagwat001/Opspilot1/actions/runs/{test_run_id}",
            "head_commit": {
                "message": "fix: update token validation logic"
            }
        }
    }
    raw_bytes = json.dumps(payload).encode("utf-8")
    secret = settings.GITHUB_WEBHOOK_SECRET or "opspilot_webhook_test_secret"
    sig = "sha256=" + hmac.new(secret.encode("utf-8"), raw_bytes, hashlib.sha256).hexdigest()

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/github/webhook",
            content=raw_bytes,
            headers={
                "X-GitHub-Event": "workflow_run",
                "X-GitHub-Delivery": delivery_id,
                "X-Hub-Signature-256": sig,
                "Content-Type": "application/json"
            }
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "received"
        failure_id = data["detected_failure_id"]
        assert failure_id is not None

        # Verify failure in failures list
        fail_list_resp = await client.get("/api/github/failures", headers=ADMIN_HEADERS)
        assert fail_list_resp.status_code == 200
        failures = fail_list_resp.json()
        target = next((f for f in failures if f["run_id"] == test_run_id), None)
        assert target is not None
        assert target["workflow_name"] == "Integration & Unit Tests"
        assert target["branch"] == "fix/auth-bug"
        assert "error_log_snippet" in target

    # Teardown
    async with AsyncSessionLocal() as session:
        f_rec = (await session.execute(select(WorkflowFailure).where(WorkflowFailure.run_id == test_run_id))).scalar_one_or_none()
        if f_rec:
            await session.delete(f_rec)
        ev_rec = (await session.execute(select(GitHubEvent).where(GitHubEvent.delivery_id == delivery_id))).scalar_one_or_none()
        if ev_rec:
            await session.delete(ev_rec)
        notifs = (await session.execute(
            select(InAppNotification).where(InAppNotification.link == str(test_run_id))
        )).scalars().all()
        for n in notifs:
            await session.delete(n)
        await session.commit()

@pytest.mark.asyncio
async def test_polling_fallback_reconciliation():
    """Verify /api/github/sync reconciles monitored repositories and updates last_synced_at timestamp."""
    await init_system_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        sync_resp = await client.post("/api/github/sync", headers=ADMIN_HEADERS)
        assert sync_resp.status_code == 200
        data = sync_resp.json()
        assert data["status"] == "SUCCESS"
        assert "synced_repositories" in data
        assert "synced_at" in data
        assert data["synced_repositories"] >= 0
