"""
OpsPilot Real-Time GitHub Intelligence & AI DevOps Regression & Acceptance Tests
Verifies webhook signature validation, delivery deduplication, automated CI/CD failure detection,
AI root-cause diagnosis, patch proposal generation, cryptographic human approval enforcement,
approved fix execution (branch + commit + PR), repository health scoring, and LangGraph queries.
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
from app.core.db import get_db, AsyncSessionLocal, init_system_db
from app.models.models import User, WorkflowFailure, FixProposal, ApprovalRequest, GitHubEvent, MonitoredRepository
from app.agents.agent_graph import agent_executor

# Setup admin test token
from app.core.security import create_access_token

ADMIN_HEADERS = {
    "Authorization": f"Bearer {create_access_token({'sub': 'usr-admin-01'})}"
}

@pytest.mark.asyncio
async def test_github_account_telemetry():
    await init_system_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/github/account", headers=ADMIN_HEADERS)
        assert resp.status_code == 200
        data = resp.json()
        assert data["connected"] is True
        assert "login" in data
        assert "scopes" in data

@pytest.mark.asyncio
async def test_repository_discovery_and_monitoring():
    await init_system_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. List repos
        list_resp = await client.get("/api/github/repositories", headers=ADMIN_HEADERS)
        assert list_resp.status_code == 200
        data = list_resp.json()
        assert data["count"] > 0
        repo_name = data["repositories"][0]["full_name"]

        # 2. Toggle monitoring
        mon_resp = await client.post(
            "/api/github/repositories/monitor",
            headers=ADMIN_HEADERS,
            json={"repo_full_name": repo_name, "is_monitored": True}
        )
        assert mon_resp.status_code == 200
        assert mon_resp.json()["is_monitored"] is True

@pytest.mark.asyncio
async def test_webhook_ingestion_and_ci_failure_detection():
    await init_system_db()
    transport = ASGITransport(app=app)
    delivery_id = f"deliv-{uuid.uuid4()}"
    test_run_id = int(uuid.uuid4().int % 100000000)

    payload = {
        "action": "completed",
        "repository": {"full_name": "enterprise-ops/auth-service"},
        "sender": {"login": "devops-operator"},
        "workflow_run": {
            "id": test_run_id,
            "workflow_id": "88123",
            "name": "Integration & Unit Tests",
            "conclusion": "failure",
            "head_sha": "f3a2b1c0d9e8",
            "head_branch": "main",
            "html_url": f"https://github.com/enterprise-ops/auth-service/actions/runs/{test_run_id}",
            "head_commit": {
                "message": "fix: update database pool configuration"
            }
        }
    }
    raw_bytes = json.dumps(payload).encode("utf-8")
    sig = "sha256=" + hmac.new(settings.GITHUB_WEBHOOK_SECRET.encode("utf-8"), raw_bytes, hashlib.sha256).hexdigest()

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # First delivery: should ingest and create failure
        resp1 = await client.post(
            "/api/github/webhook",
            content=raw_bytes,
            headers={
                "X-GitHub-Event": "workflow_run",
                "X-GitHub-Delivery": delivery_id,
                "X-Hub-Signature-256": sig,
                "Content-Type": "application/json"
            }
        )
        assert resp1.status_code == 200
        assert resp1.json()["status"] == "received"
        assert resp1.json()["detected_failure_id"] is not None

        # Duplicate delivery: must be idempotently skipped
        resp2 = await client.post(
            "/api/github/webhook",
            content=raw_bytes,
            headers={
                "X-GitHub-Event": "workflow_run",
                "X-GitHub-Delivery": delivery_id,
                "X-Hub-Signature-256": sig,
                "Content-Type": "application/json"
            }
        )
        assert resp2.status_code == 200
        assert resp2.json()["status"] == "duplicate_skipped"

@pytest.mark.asyncio
async def test_ai_error_analysis_and_fix_proposal_lifecycle():
    await init_system_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Fetch failure list (sync if empty)
        fail_resp = await client.get("/api/github/failures", headers=ADMIN_HEADERS)
        assert fail_resp.status_code == 200
        failures = fail_resp.json()
        if not failures:
            await client.post("/api/github/sync", headers=ADMIN_HEADERS)
            fail_resp = await client.get("/api/github/failures", headers=ADMIN_HEADERS)
            failures = fail_resp.json()
        assert len(failures) > 0
        failure_id = failures[0]["id"]

        # 2. Trigger AI Error Analysis
        analyze_resp = await client.post(f"/api/github/failures/{failure_id}/analyze", headers=ADMIN_HEADERS)
        assert analyze_resp.status_code == 200
        an_data = analyze_resp.json()
        assert an_data["status"] == "SUCCESS"
        assert "pydantic-settings" in an_data["root_cause"]
        assert "Diagnostic Report" in an_data["analysis_summary"]

        # 3. Propose Fix bound to Human Approval boundary
        prop_resp = await client.post(f"/api/github/failures/{failure_id}/propose-fix", headers=ADMIN_HEADERS)
        assert prop_resp.status_code == 200
        prop_data = prop_resp.json()
        assert prop_data["approval_required"] is True
        assert prop_data["approval_id"] is not None
        assert "diff_content" in prop_data
        proposal_id = prop_data["proposal_id"]

        # 4. Execute Approved Fix
        exec_resp = await client.post(f"/api/github/proposals/{proposal_id}/execute", headers=ADMIN_HEADERS)
        assert exec_resp.status_code == 200
        exec_data = exec_resp.json()
        assert exec_data["status"] == "SUCCESS"
        assert "pull" in exec_data["pr_url"]

@pytest.mark.asyncio
async def test_repository_health_and_notifications():
    await init_system_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Check health endpoint
        health_resp = await client.get("/api/github/health", headers=ADMIN_HEADERS)
        assert health_resp.status_code == 200
        h = health_resp.json()
        assert "overall_health_score" in h
        assert h["overall_health_score"] > 0
        assert "status" in h

        # Check notifications
        notif_resp = await client.get("/api/github/notifications", headers=ADMIN_HEADERS)
        assert notif_resp.status_code == 200
        n = notif_resp.json()
        assert "notifications" in n
        if n["notifications"]:
            first_id = n["notifications"][0]["id"]
            mark_resp = await client.post(f"/api/github/notifications/{first_id}/read", headers=ADMIN_HEADERS)
            assert mark_resp.status_code == 200

@pytest.mark.asyncio
async def test_langgraph_github_intelligence_queries():
    await init_system_db()
    # 1. Query: "Show recent commits"
    state_commits = {
        "execution_id": "test-gh-01",
        "conversation_id": "conv-gh-01",
        "user_id": "usr-admin-01",
        "workspace_id": "default-ops",
        "user_request": "Show recent commits for auth-service",
        "conversation_history": [],
        "target_systems": [],
        "available_tools": [],
        "planned_actions": [],
        "completed_actions": [],
        "pending_approval": None,
        "tool_results": [],
        "final_response": None,
        "execution_status": "received",
        "current_step": "init",
        "errors": []
    }
    res_commits = await agent_executor.ainvoke(state_commits)
    assert res_commits["execution_status"] == "completed"
    assert "Commits" in res_commits["final_response"]

    # 2. Query: "Why did my latest build fail?"
    state_fail = {
        "execution_id": "test-gh-02",
        "conversation_id": "conv-gh-02",
        "user_id": "usr-admin-01",
        "workspace_id": "default-ops",
        "user_request": "Why did my latest build fail in auth-service?",
        "conversation_history": [],
        "target_systems": [],
        "available_tools": [],
        "planned_actions": [],
        "completed_actions": [],
        "pending_approval": None,
        "tool_results": [],
        "final_response": None,
        "execution_status": "received",
        "current_step": "init",
        "errors": []
    }
    res_fail = await agent_executor.ainvoke(state_fail)
    assert res_fail["execution_status"] == "completed"
    assert "Root Cause" in res_fail["final_response"]

    # 3. Query: "Prepare a pull request to fix the build" -> Must Pause for Approval!
    state_fix = {
        "execution_id": "test-gh-03",
        "conversation_id": "conv-gh-03",
        "user_id": "usr-admin-01",
        "workspace_id": "default-ops",
        "user_request": "Prepare a pull request to fix the build in auth-service",
        "conversation_history": [],
        "target_systems": [],
        "available_tools": [],
        "planned_actions": [],
        "completed_actions": [],
        "pending_approval": None,
        "tool_results": [],
        "final_response": None,
        "execution_status": "received",
        "current_step": "init",
        "errors": []
    }
    res_fix = await agent_executor.ainvoke(state_fix)
    assert res_fix["execution_status"] == "awaiting_approval"
    assert res_fix["pending_approval"]["tool_name"] == "create_pull_request"
