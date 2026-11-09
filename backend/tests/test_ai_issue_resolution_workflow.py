"""
OpsPilot AI Issue Analysis, Verified Fix Execution, and Detailed Solution History Tests
Tests all 10 implementation phases of the end-to-end evidence-based resolution lifecycle:
- AI Analysis generation with 7 structured sections
- Root cause diagnosis and log evidence
- Isolated scratch sandbox verification
- Strict human approval enforcement
- Real GitHub PR state handling
- Post-merge resolution verification (VERIFIED_RESOLVED vs STILL_FAILING vs NOT_VERIFIED)
- Enterprise Audit Log solution history recording
- 8-part "View Solution" payload retrieval
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
from app.models.models import (
    WorkflowFailure, FixProposal, ApprovalRequest, AuditLog, MonitoredRepository
)
from sqlalchemy import select

ADMIN_HEADERS = {
    "Authorization": f"Bearer {create_access_token({'sub': 'usr-admin-01'})}"
}

VIEWER_HEADERS = {
    "Authorization": f"Bearer {create_access_token({'sub': 'usr-viewer-01'})}"
}

TEST_REPO = "adityabhagwat001/Opspilot1"

async def ensure_test_context():
    """Ensure monitored repository and test users exist in the database."""
    async with AsyncSessionLocal() as db:
        from app.models.models import User, WorkspaceMember
        from app.core.security import hash_password

        usr_res = await db.execute(select(User).where(User.id == "usr-viewer-01"))
        if not usr_res.scalar_one_or_none():
            db.add(User(
                id="usr-viewer-01",
                email="viewer@opspilot.internal",
                full_name="Viewer User",
                hashed_password=hash_password("viewer123"),
                role="viewer",
                is_active=True
            ))
            db.add(WorkspaceMember(
                workspace_id="default-ops",
                user_id="usr-viewer-01",
                role="viewer"
            ))

        repo_res = await db.execute(
            select(MonitoredRepository).where(MonitoredRepository.full_name == TEST_REPO)
        )
        repo = repo_res.scalar_one_or_none()
        if not repo:
            repo = MonitoredRepository(
                workspace_id="default-ops",
                owner="adityabhagwat001",
                name="Opspilot1",
                full_name=TEST_REPO,
                default_branch="main",
                is_active=True,
                health_score=100
            )
            db.add(repo)
        else:
            repo.is_active = True

        await db.commit()

@pytest.mark.asyncio
async def test_ai_issue_analysis_generation():
    """
    Phase 2 & 3: Tests 'Analyze with AI' endpoint:
    - Retries logs / failing step
    - Calls Groq analysis service
    - Returns all 7 structured sections
    - Emits AI_ANALYSIS_COMPLETED audit record
    """
    await ensure_test_context()
    async with AsyncSessionLocal() as db:
        failure_id = f"fail-test-{uuid.uuid4().hex[:8]}"
        failure = WorkflowFailure(
            id=failure_id,
            workspace_id="default-ops",
            repo_full_name=TEST_REPO,
            workflow_name="CI Test Suite",
            run_id=9988112233,
            commit_sha="a1b2c3d4e5f6789012345678901234567890abcd",
            commit_message="Add initial config settings",
            branch="main",
            actor="adityabhagwat001",
            failing_step="Run Pytest & Build Verification",
            error_log_snippet="ModuleNotFoundError: No module named 'pydantic_settings'\nImportError: cannot import name 'BaseSettings' from 'pydantic'",
            status="detected"
        )
        db.add(failure)
        await db.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.post(f"/api/github/failures/{failure_id}/analyze", headers=ADMIN_HEADERS)
        assert res.status_code == 200, res.text
        data = res.json()

        assert data["status"] == "SUCCESS"
        assert data["failure_id"] == failure_id
        assert data["analysis_status"] == "ANALYZED"
        assert "pydantic" in data["root_cause"].lower()

        # Verify all 7 structured sections are present in structured_analysis
        sa = data.get("structured_analysis")
        assert sa is not None
        assert "problem_summary" in sa and len(sa["problem_summary"]) > 0
        assert "root_cause" in sa and len(sa["root_cause"]) > 0
        assert "recommended_solution" in sa and len(sa["recommended_solution"]) > 0
        assert "files_requiring_changes" in sa and isinstance(sa["files_requiring_changes"], list)
        assert "code_changes_diff" in sa and isinstance(sa["code_changes_diff"], str)
        assert "risk_assessment" in sa and len(sa["risk_assessment"]) > 0
        assert "expected_result" in sa and len(sa["expected_result"]) > 0

    # Verify Audit Log entry created
    async with AsyncSessionLocal() as db:
        audit_res = await db.execute(
            select(AuditLog).where(
                AuditLog.failure_id == failure_id,
                AuditLog.action_type == "AI_ANALYSIS_COMPLETED"
            )
        )
        audit_item = audit_res.scalar_one_or_none()
        assert audit_item is not None
        assert audit_item.solution_history_json is not None

@pytest.mark.asyncio
async def test_propose_fix_sandbox_verification_and_approval_enforcement():
    """
    Phase 4 & 5: Tests that proposing a fix validates patch in scratch sandbox,
    creates an ApprovalRequest, and strictly blocks code modifications until approved.
    """
    await ensure_test_context()
    async with AsyncSessionLocal() as db:
        failure_id = f"fail-test-{uuid.uuid4().hex[:8]}"
        failure = WorkflowFailure(
            id=failure_id,
            workspace_id="default-ops",
            repo_full_name=TEST_REPO,
            workflow_name="CI Test Suite",
            run_id=9988445566,
            commit_sha="c1d2e3f4a5b67890123456789012345678901234",
            commit_message="Update dependencies",
            branch="main",
            actor="adityabhagwat001",
            failing_step="Run Pytest & Build Verification",
            error_log_snippet="ModuleNotFoundError: No module named 'pydantic_settings'",
            status="analyzed"
        )
        db.add(failure)
        await db.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # 1. Propose Fix
        res = await ac.post(f"/api/github/failures/{failure_id}/propose-fix", headers=ADMIN_HEADERS)
        assert res.status_code == 200, res.text
        prop_data = res.json()

        assert prop_data["status"] == "SUCCESS"
        assert prop_data["sandbox_verified"] is True
        assert prop_data["approval_required"] is True
        proposal_id = prop_data["proposal_id"]
        approval_id = prop_data["approval_id"]

        # 2. Reject the approval request
        rej_res = await ac.post(f"/api/approvals/{approval_id}/reject", json={"reason": "Human reviewer requested modifications"}, headers=ADMIN_HEADERS)
        assert rej_res.status_code == 200, rej_res.text

        # 3. Verify Execution is strictly BLOCKED after rejection
        exec_res = await ac.post(f"/api/github/proposals/{proposal_id}/execute", headers=ADMIN_HEADERS)
        assert exec_res.status_code == 400, "Must block execution when human approval is rejected"
        assert "cannot approve" in exec_res.text.lower() or "rejected" in exec_res.text.lower()

@pytest.mark.asyncio
async def test_post_merge_resolution_verification_success():
    """
    Phase 6: Tests that post-fix resolution verification confirms the fix
    only when live GitHub Actions workflow concluded with SUCCESS.
    """
    await ensure_test_context()
    async with AsyncSessionLocal() as db:
        failure_id = f"fail-verif-{uuid.uuid4().hex[:8]}"
        failure = WorkflowFailure(
            id=failure_id,
            workspace_id="default-ops",
            repo_full_name=TEST_REPO,
            workflow_name="CI Test Suite",
            run_id=9988770001,
            commit_sha="e1e2e3e4e5e67890123456789012345678901234",
            branch="main",
            status="fix_applied",
            resolution_status="NOT_VERIFIED"
        )
        db.add(failure)

        proposal_id = f"prop-verif-{uuid.uuid4().hex[:8]}"
        proposal = FixProposal(
            id=proposal_id,
            workspace_id="default-ops",
            failure_id=failure_id,
            repo_full_name=TEST_REPO,
            target_branch="main",
            fix_branch=f"opspilot-fix/run-9988770001",
            title="Fix: Resolve CI/CD build error in CI Test Suite",
            explanation="Added pydantic-settings dependency",
            files_modified_json=json.dumps([{"path": "requirements.txt", "change_summary": "Added pydantic-settings>=2.0"}]),
            diff="--- a/requirements.txt\n+++ b/requirements.txt\n@@ -1 +1,2 @@\n-r backend/requirements.txt\n+pydantic-settings>=2.0",
            status="applied",
            pr_number=3,
            pull_request_url="https://github.com/adityabhagwat001/Opspilot1/pull/3",
            pr_state="MERGED",
            resolution_status="NOT_VERIFIED"
        )
        db.add(proposal)
        await db.commit()

    # Mock GitHub PR response (merged) and Actions workflow runs response (passed)
    async def mock_github_get(client, url, *args, **kwargs):
        url_str = str(url)
        if "/pulls/3" in url_str:
            return Response(200, json={
                "number": 3,
                "html_url": "https://github.com/adityabhagwat001/Opspilot1/pull/3",
                "state": "closed",
                "merged": True,
                "merged_at": "2026-11-01T10:00:00Z",
                "merge_commit_sha": "merge-sha-1234567890abcdef"
            })
        elif "/actions/runs" in url_str:
            return Response(200, json={
                "workflow_runs": [
                    {
                        "id": 8877665544,
                        "name": "CI Test Suite",
                        "head_branch": "main",
                        "head_sha": "merge-sha-1234567890abcdef",
                        "status": "completed",
                        "conclusion": "success",
                        "html_url": "https://github.com/adityabhagwat001/Opspilot1/actions/runs/8877665544",
                        "created_at": "2026-11-01T10:05:00Z"
                    }
                ]
            })
        return Response(404, json={})

    with patch.object(AsyncClient, "get", new=mock_github_get):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            res = await ac.post(f"/api/github/proposals/{proposal_id}/verify", headers=ADMIN_HEADERS)
            assert res.status_code == 200, res.text
            data = res.json()

            assert data["resolution_status"] == "VERIFIED_RESOLVED"
            assert data["pr_status"] == "MERGED"
            assert "verified" in data["verification"]["final_result_explanation"].lower()

    # Verify state in database is updated
    async with AsyncSessionLocal() as db:
        p_chk = (await db.execute(select(FixProposal).where(FixProposal.id == proposal_id))).scalar_one()
        assert p_chk.resolution_status == "VERIFIED_RESOLVED"
        assert p_chk.merge_commit_sha == "merge-sha-1234567890abcdef"

        f_chk = (await db.execute(select(WorkflowFailure).where(WorkflowFailure.id == failure_id))).scalar_one()
        assert f_chk.resolution_status == "VERIFIED_RESOLVED"

@pytest.mark.asyncio
async def test_post_merge_resolution_verification_still_failing():
    """
    Phase 6: Tests that if post-merge workflow fails, status is correctly marked STILL_FAILING.
    """
    await ensure_test_context()
    async with AsyncSessionLocal() as db:
        failure_id = f"fail-fail-{uuid.uuid4().hex[:8]}"
        failure = WorkflowFailure(
            id=failure_id,
            workspace_id="default-ops",
            repo_full_name=TEST_REPO,
            workflow_name="CI Test Suite",
            run_id=9988770002,
            commit_sha="f1f2f3f4f5f67890123456789012345678901234",
            branch="main",
            status="fix_applied",
            resolution_status="NOT_VERIFIED"
        )
        db.add(failure)

        proposal_id = f"prop-fail-{uuid.uuid4().hex[:8]}"
        proposal = FixProposal(
            id=proposal_id,
            workspace_id="default-ops",
            failure_id=failure_id,
            repo_full_name=TEST_REPO,
            target_branch="main",
            fix_branch=f"opspilot-fix/run-9988770002",
            title="Fix: Incomplete patch",
            explanation="Partial fix attempt",
            status="applied",
            pr_number=4,
            pull_request_url="https://github.com/adityabhagwat001/Opspilot1/pull/4",
            pr_state="MERGED",
            resolution_status="NOT_VERIFIED"
        )
        db.add(proposal)
        await db.commit()

    async def mock_github_failing_get(client, url, *args, **kwargs):
        url_str = str(url)
        if "/pulls/4" in url_str:
            return Response(200, json={
                "number": 4,
                "html_url": "https://github.com/adityabhagwat001/Opspilot1/pull/4",
                "state": "closed",
                "merged": True,
                "merged_at": "2026-11-01T10:00:00Z",
                "merge_commit_sha": "failing-merge-sha"
            })
        elif "/actions/runs" in url_str:
            return Response(200, json={
                "workflow_runs": [
                    {
                        "id": 8877665599,
                        "name": "CI Test Suite",
                        "head_branch": "main",
                        "head_sha": "failing-merge-sha",
                        "status": "completed",
                        "conclusion": "failure",
                        "html_url": "https://github.com/adityabhagwat001/Opspilot1/actions/runs/8877665599"
                    }
                ]
            })
        return Response(404, json={})

    with patch.object(AsyncClient, "get", new=mock_github_failing_get):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            res = await ac.post(f"/api/github/proposals/{proposal_id}/verify", headers=ADMIN_HEADERS)
            assert res.status_code == 200, res.text
            data = res.json()
            assert data["resolution_status"] == "STILL_FAILING"

@pytest.mark.asyncio
async def test_audit_log_and_view_solution_history():
    """
    Phase 7 & 8: Tests that the Audit Log includes solution metadata and
    GET /api/audit/{audit_id}/solution returns the full 8-part resolution history.
    """
    await ensure_test_context()
    async with AsyncSessionLocal() as db:
        failure_id = f"fail-audit-{uuid.uuid4().hex[:8]}"
        failure = WorkflowFailure(
            id=failure_id,
            workspace_id="default-ops",
            repo_full_name=TEST_REPO,
            workflow_name="CI Test Suite",
            run_id=9988776655,
            commit_sha="a1b2c3d4e5f6789012345678901234567890abcd",
            branch="main",
            failing_step="Run Pytest & Build Verification",
            error_log_snippet="ModuleNotFoundError: No module named 'pydantic_settings'",
            root_cause="Required dependency 'pydantic-settings' missing from requirements.txt",
            status="resolved",
            resolution_status="VERIFIED_RESOLVED"
        )
        db.add(failure)

        proposal_id = f"prop-audit-{uuid.uuid4().hex[:8]}"
        proposal = FixProposal(
            id=proposal_id,
            workspace_id="default-ops",
            failure_id=failure_id,
            repo_full_name=TEST_REPO,
            target_branch="main",
            fix_branch="opspilot-fix/run-9988776655",
            title="Fix: Resolve CI/CD build error in CI Test Suite (#9988776655)",
            explanation="Add pydantic-settings package",
            diff="--- a/requirements.txt\n+++ b/requirements.txt\n@@ -1 +1,2 @@\n-r backend/requirements.txt\n+pydantic-settings>=2.0",
            files_modified_json=json.dumps([{
                "path": "requirements.txt",
                "change_summary": "Added pydantic-settings>=2.0",
                "added_lines": ["pydantic-settings>=2.0"],
                "removed_lines": []
            }]),
            test_results_json=json.dumps({
                "sandbox_status": "PASSED",
                "passed_checks": ["AST Syntax check passed (0 errors)", "Pip package spec verified"],
                "failed_checks": []
            }),
            status="applied",
            pr_number=3,
            pull_request_url="https://github.com/adityabhagwat001/Opspilot1/pull/3",
            pr_state="MERGED",
            resolution_status="VERIFIED_RESOLVED",
            merge_commit_sha="a1b2c3d4e5f6789012345678901234567890abcd"
        )
        db.add(proposal)

        audit_id = f"aud-test-{uuid.uuid4().hex[:8]}"
        audit = AuditLog(
            id=audit_id,
            workspace_id="default-ops",
            user_id="usr-admin-01",
            action_type="WRITE_EXECUTED",
            target_system="github",
            tool_name="create_pull_request",
            proposal_id=proposal_id,
            failure_id=failure_id,
            repo_full_name=TEST_REPO,
            result_summary="Fix executed: Created Pull Request #3",
            status="success"
        )
        db.add(audit)
        await db.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # 1. Query Audit Log list
        audit_res = await ac.get("/api/audit", headers=ADMIN_HEADERS)
        assert audit_res.status_code == 200
        logs = audit_res.json()
        target_log = next((l for l in logs if l["id"] == audit_id), None)
        assert target_log is not None
        assert target_log["has_solution"] is True
        assert target_log["proposal_id"] == proposal_id
        assert target_log["failure_id"] == failure_id

        # 2. Query Solution History endpoint
        sol_res = await ac.get(f"/api/audit/{audit_id}/solution", headers=ADMIN_HEADERS)
        assert sol_res.status_code == 200, sol_res.text
        sol = sol_res.json()

        # Check all 8 sections
        assert "issue_overview" in sol
        assert sol["issue_overview"]["repo"] == TEST_REPO
        assert sol["issue_overview"]["workflow_run_id"] == 9988776655
        assert sol["issue_overview"]["resolution_status"] == "VERIFIED_RESOLVED"

        assert "problem_summary" in sol and len(sol["problem_summary"]) > 0
        assert "root_cause" in sol and "technical_cause" in sol["root_cause"]
        assert "suggested_solution" in sol and "bullet_points" in sol["suggested_solution"]
        assert "code_changes" in sol and "requirements.txt" in sol["code_changes"]["diff"]
        assert "testing_evidence" in sol and "PASSED" in sol["testing_evidence"]["sandbox_status"]
        assert "pr_details" in sol and sol["pr_details"]["pr_number"] == 3
        assert "final_result" in sol and sol["final_result"]["status"] == "VERIFIED_RESOLVED"

        # 3. Query direct proposal solution endpoint
        prop_sol_res = await ac.get(f"/api/github/proposals/{proposal_id}/solution", headers=ADMIN_HEADERS)
        assert prop_sol_res.status_code == 200
        assert prop_sol_res.json()["final_result"]["status"] == "VERIFIED_RESOLVED"

@pytest.mark.asyncio
async def test_rbac_unauthorized_access_rejection():
    """
    Phase 10: Ensures viewers or unauthenticated users cannot trigger write actions
    like proposing fixes or executing patches.
    """
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # 1. Propose fix with viewer token -> 403 Forbidden
        res = await ac.post("/api/github/failures/any-fail-id/propose-fix", headers=VIEWER_HEADERS)
        assert res.status_code == 403

        # 2. Execute fix with viewer token -> 403 Forbidden
        res = await ac.post("/api/github/proposals/any-prop-id/execute", headers=VIEWER_HEADERS)
        assert res.status_code == 403
