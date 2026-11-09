"""
Comprehensive Verification Tests for GitHub Pull Request Status, Workflow Association,
and Notification Synchronization in OpsPilot.
"""

import pytest
import uuid
import json
import datetime
from httpx import AsyncClient, ASGITransport, Response
from unittest.mock import patch, AsyncMock
from app.main import app
from app.core.db import AsyncSessionLocal, init_system_db
from app.core.security import create_access_token
from app.models.models import WorkflowFailure, FixProposal, InAppNotification, ApprovalRequest
from app.api.github_ops import fetch_github_pr_live_status, _pr_status_cache
from app.approvals.approval_service import approval_service
from sqlalchemy import select

ADMIN_HEADERS = {
    "Authorization": f"Bearer {create_access_token({'sub': 'usr-admin-01'})}"
}

@pytest.mark.asyncio
async def test_pr_status_helper_live_states():
    """Verify fetch_github_pr_live_status returns correct states for various GitHub responses."""
    _pr_status_cache.clear()

    # Case 1: PR is Open
    with patch.object(AsyncClient, "get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = Response(
            status_code=200,
            json={
                "number": 42,
                "html_url": "https://github.com/adityabhagwat001/Opspilot1/pull/42",
                "title": "Fix memory leak",
                "state": "open",
                "merged": False,
                "head": {"ref": "fix-branch-42"},
                "base": {"ref": "main"}
            }
        )

        res = await fetch_github_pr_live_status("adityabhagwat001", "Opspilot1", 42)
        assert res["pr_status"] == "OPEN"
        assert res["number"] == 42
        assert res["html_url"] == "https://github.com/adityabhagwat001/Opspilot1/pull/42"

    _pr_status_cache.clear()
    # Case 2: PR is Merged
    with patch.object(AsyncClient, "get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = Response(
            status_code=200,
            json={
                "number": 1,
                "html_url": "https://github.com/adityabhagwat001/Opspilot1/pull/1",
                "title": "CI Fix",
                "state": "closed",
                "merged": True,
                "merged_at": "2026-10-17T12:00:00Z",
                "head": {"ref": "patch-1"},
                "base": {"ref": "main"}
            }
        )

        res = await fetch_github_pr_live_status("adityabhagwat001", "Opspilot1", 1)
        assert res["pr_status"] == "MERGED"
        assert res["merged"] is True

    _pr_status_cache.clear()
    # Case 3: PR is Closed without merging
    with patch.object(AsyncClient, "get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = Response(
            status_code=200,
            json={
                "number": 99,
                "html_url": "https://github.com/adityabhagwat001/Opspilot1/pull/99",
                "title": "Abandoned fix",
                "state": "closed",
                "merged": False,
                "merged_at": None,
                "head": {"ref": "abandoned-branch"},
                "base": {"ref": "main"}
            }
        )

        res = await fetch_github_pr_live_status("adityabhagwat001", "Opspilot1", 99)
        assert res["pr_status"] == "CLOSED"

    _pr_status_cache.clear()
    # Case 4: PR does not exist (404) -> NOT_CREATED
    with patch.object(AsyncClient, "get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = Response(status_code=404)

        res = await fetch_github_pr_live_status("adityabhagwat001", "Opspilot1", 99999)
        assert res["pr_status"] == "NOT_CREATED"

    _pr_status_cache.clear()
    # Case 5: GitHub API error (401 Unauthorized / Token Error) -> ERROR
    with patch.object(AsyncClient, "get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = Response(status_code=401, json={"message": "Bad credentials"})

        res = await fetch_github_pr_live_status("some-org", "some-repo", 10)
        assert res["pr_status"] == "ERROR"

    _pr_status_cache.clear()
    # Case 6: None or 0 PR number -> NOT_CREATED
    res_none = await fetch_github_pr_live_status("adityabhagwat001", "Opspilot1", None)
    assert res_none["pr_status"] == "NOT_CREATED"


@pytest.mark.asyncio
async def test_workflow_run_9988776655_never_associates_pr_1():
    """Verify that workflow run 9988776655 is never falsely associated with PR #1."""
    await init_system_db()
    transport = ASGITransport(app=app)

    async with AsyncSessionLocal() as session:
        # Create a failure for run 9988776655
        test_fail_id = f"wf-test-disassoc-{uuid.uuid4().hex[:8]}"
        fail = WorkflowFailure(
            id=test_fail_id,
            workspace_id="default-ops",
            repo_full_name="adityabhagwat001/Opspilot1",
            workflow_name="CI Test Suite",
            run_id=9988776655,
            commit_sha="a1b2c3d4e5f6789012345678901234567890abcd",
            head_branch="main",
            actor="operator",
            status="fix_applied"
        )
        session.add(fail)

        # Create proposal associated with run 9988776655
        test_prop_id = f"prop-test-{uuid.uuid4().hex[:8]}"
        prop = FixProposal(
            id=test_prop_id,
            workspace_id="default-ops",
            failure_id=test_fail_id,
            repo_full_name="adityabhagwat001/Opspilot1",
            fix_branch="opspilot-fix/run-9988776655",
            title="Fix: Resolve CI/CD build error in CI Test Suite (#9988776655)",
            explanation="Test explanation",
            diff="--- a/requirements.txt",
            status="applied",
            pull_request_url="https://github.com/adityabhagwat001/Opspilot1/pull/1",
            pr_number=1,
            pr_state="NOT_CREATED"
        )
        session.add(prop)
        await session.commit()

    try:
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/github/proposals", headers=ADMIN_HEADERS)
            assert resp.status_code == 200
            props = resp.json()

            # Find our proposal
            target_p = next((p for p in props if p["id"] == test_prop_id), None)
            assert target_p is not None
            # Verified: it must NOT have PR #1 or PR URL, and pr_status MUST be NOT_CREATED
            assert target_p["workflow_run_id"] == 9988776655
            assert target_p["pr_number"] is None
            assert target_p["pr_url"] is None
            assert target_p["pr_status"] == "NOT_CREATED"
            # Execution status is applied, but PR status is NOT_CREATED
            assert target_p["status"] == "applied"
    finally:
        # Clean up
        async with AsyncSessionLocal() as session:
            p_rec = (await session.execute(select(FixProposal).where(FixProposal.id == test_prop_id))).scalar_one_or_none()
            if p_rec:
                await session.delete(p_rec)
            f_rec = (await session.execute(select(WorkflowFailure).where(WorkflowFailure.id == test_fail_id))).scalar_one_or_none()
            if f_rec:
                await session.delete(f_rec)
            await session.commit()


@pytest.mark.asyncio
async def test_execute_approved_fix_failure_does_not_mark_applied():
    """Verify that when PR creation returns an error, proposal is not marked applied and real error is shown."""
    await init_system_db()
    transport = ASGITransport(app=app)

    test_prop_id = f"prop-test-err-{uuid.uuid4().hex[:8]}"

    async with AsyncSessionLocal() as session:
        appr = await approval_service.create_approval_request(
            db=session,
            execution_id=f"exec-test-{uuid.uuid4().hex[:8]}",
            user_id="usr-admin-01",
            workspace_id="default-ops",
            target_system="github",
            tool_name="create_pull_request",
            arguments={"owner": "adityabhagwat001", "repo": "Opspilot1"},
            action_summary="Open Pull Request",
            target_resource="adityabhagwat001/Opspilot1"
        )
        test_appr_id = appr.id

        prop = FixProposal(
            id=test_prop_id,
            workspace_id="default-ops",
            repo_full_name="adityabhagwat001/Opspilot1",
            fix_branch="opspilot-fix/test-fail",
            title="Fix: Resolve bug",
            explanation="Explanation",
            approval_id=test_appr_id,
            status="proposed"
        )
        session.add(prop)
        await session.commit()

    try:
        # Mock approval_service to return a tool execution error
        mock_exec_result = {
            "status": "EXECUTED",
            "approval_id": test_appr_id,
            "execution_result": {
                "status": "error",
                "error": "Failed to create fix branch: Reference already exists",
                "error_category": "PROVIDER_ERROR"
            }
        }
        with patch("app.approvals.approval_service.approval_service.approve_and_execute", return_value=mock_exec_result):
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post(f"/api/github/proposals/{test_prop_id}/execute", headers=ADMIN_HEADERS)
                # Must return error 400 with detail
                assert resp.status_code == 400
                assert "Failed to create fix branch" in resp.json()["detail"]

        # Verify DB state: proposal must be 'failed', not 'applied'
        async with AsyncSessionLocal() as session:
            p_check = (await session.execute(select(FixProposal).where(FixProposal.id == test_prop_id))).scalar_one()
            assert p_check.status == "failed"
            assert p_check.pr_state == "ERROR"
            assert p_check.pull_request_url is None
            assert p_check.pr_number is None

    finally:
        async with AsyncSessionLocal() as session:
            p_rec = (await session.execute(select(FixProposal).where(FixProposal.id == test_prop_id))).scalar_one_or_none()
            if p_rec:
                await session.delete(p_rec)
            a_rec = (await session.execute(select(ApprovalRequest).where(ApprovalRequest.id == test_appr_id))).scalar_one_or_none()
            if a_rec:
                await session.delete(a_rec)
            await session.commit()


@pytest.mark.asyncio
async def test_notification_synchronization_clears_stale_pr1():
    """Verify that dashboard notification endpoint updates stale notification messages referencing guessed PR #1."""
    await init_system_db()
    transport = ASGITransport(app=app)

    notif_id = f"notif-test-{uuid.uuid4().hex[:8]}"
    async with AsyncSessionLocal() as session:
        notif = InAppNotification(
            id=notif_id,
            workspace_id="default-ops",
            user_id="usr-admin-01",
            title="Fix Applied & Pull Request Opened",
            message="Pull request # created for adityabhagwat001/Opspilot1: https://github.com/adityabhagwat001/Opspilot1/pull/1",
            category="fix_executed"
        )
        session.add(notif)
        await session.commit()

    try:
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/github/notifications", headers=ADMIN_HEADERS)
            assert resp.status_code == 200
            data = resp.json()
            notifs = data["notifications"]

            target_n = next((n for n in notifs if n["id"] == notif_id), None)
            assert target_n is not None
            assert target_n["title"] == "Fix Applied to Branch (No Pull Request Created)"
            assert "pull/1" not in target_n["message"]
            assert "No pull request was created" in target_n["message"]

    finally:
        async with AsyncSessionLocal() as session:
            n_rec = (await session.execute(select(InAppNotification).where(InAppNotification.id == notif_id))).scalar_one_or_none()
            if n_rec:
                await session.delete(n_rec)
            await session.commit()


@pytest.mark.asyncio
async def test_webhook_pull_request_closed_merged_updates_proposal():
    """Verify that receiving a pull_request closed/merged webhook updates proposal pr_state."""
    await init_system_db()
    transport = ASGITransport(app=app)

    test_prop_id = f"prop-webhook-{uuid.uuid4().hex[:8]}"
    async with AsyncSessionLocal() as session:
        prop = FixProposal(
            id=test_prop_id,
            workspace_id="default-ops",
            repo_full_name="adityabhagwat001/Opspilot1",
            fix_branch="opspilot-fix/feature-x",
            title="Fix: Feature X",
            explanation="Explanation",
            pr_number=77,
            pull_request_url="https://github.com/adityabhagwat001/Opspilot1/pull/77",
            status="applied",
            pr_state="OPEN"
        )
        session.add(prop)
        await session.commit()

    try:
        webhook_payload = {
            "action": "closed",
            "repository": {
                "full_name": "adityabhagwat001/Opspilot1"
            },
            "sender": {
                "login": "adityabhagwat001"
            },
            "pull_request": {
                "number": 77,
                "title": "Fix: Feature X",
                "merged": True
            }
        }
        raw_body = json.dumps(webhook_payload).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "X-GitHub-Event": "pull_request",
            "X-GitHub-Delivery": str(uuid.uuid4())
        }

        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/api/github/webhook", content=raw_body, headers=headers)
            assert resp.status_code == 200

        # Verify proposal pr_state was updated to MERGED
        async with AsyncSessionLocal() as session:
            p_check = (await session.execute(select(FixProposal).where(FixProposal.id == test_prop_id))).scalar_one()
            assert p_check.pr_state == "MERGED"

    finally:
        async with AsyncSessionLocal() as session:
            p_rec = (await session.execute(select(FixProposal).where(FixProposal.id == test_prop_id))).scalar_one_or_none()
            if p_rec:
                await session.delete(p_rec)
            # Clean up test webhook notification for PR 77
            notifs_77 = (await session.execute(
                select(InAppNotification).where(
                    (InAppNotification.category == "pull_request") & (InAppNotification.link == "77")
                )
            )).scalars().all()
            for n in notifs_77:
                await session.delete(n)
            await session.commit()
