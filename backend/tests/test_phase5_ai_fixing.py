"""
OpsPilot Phase 5: Safe AI-Assisted Code Fixing with Isolated Test Verification Tests
Verifies:
- Grounded AI error diagnosis: Root cause derived strictly from failure log snippets (ModuleNotFoundError, ImportError, SyntaxError, AssertionError)
- Strict unified diff validation: Conformance to unified diff specification with origin/destination and hunk headers
- Isolated scratch/sandbox verification: Pre-flight AST/syntax compilation in temporary sandbox before human approval generation
- Protection against syntax errors and malicious tokens in patches
- End-to-end integration: Failure -> Grounded Analysis -> Sandbox Verification -> Human Approval Gate
"""

import os
import json
import uuid
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.db import AsyncSessionLocal, init_system_db
from app.core.security import create_access_token
from app.models.models import WorkflowFailure, FixProposal, ApprovalRequest
from sqlalchemy import select
from app.api.github_ops import (
    validate_unified_diff,
    verify_patch_in_sandbox,
    diagnose_failure_from_log
)

ADMIN_HEADERS = {
    "Authorization": f"Bearer {create_access_token({'sub': 'usr-admin-01'})}"
}

def test_diagnose_failure_from_log_grounding():
    """Verify error diagnosis extracts grounded root causes from distinct log outputs."""
    # 1. ModuleNotFoundError
    log_module = "Traceback (most recent call last):\nModuleNotFoundError: No module named 'httpx'\nProcess completed with exit code 1."
    diag_module = diagnose_failure_from_log(log_module, "Run pytest", "test-org/repo1")
    assert diag_module["error_type"] == "ModuleNotFoundError"
    assert "httpx" in diag_module["root_cause"]
    assert diag_module["missing_pkg"] == "httpx"
    assert diag_module["target_file"] == "requirements.txt"

    # 2. ImportError with BaseSettings from pydantic
    log_import = "ImportError: cannot import name 'BaseSettings' from 'pydantic'"
    diag_import = diagnose_failure_from_log(log_import, "Import models", "test-org/repo1")
    assert diag_import["error_type"] == "ImportError"
    assert "BaseSettings" in diag_import["root_cause"]
    assert diag_import["missing_pkg"] == "pydantic-settings"

    # 3. SyntaxError
    log_syntax = '  File "backend/app/router.py", line 45\n    def broken(\nSyntaxError: invalid syntax'
    diag_syntax = diagnose_failure_from_log(log_syntax, "Lint & compile", "test-org/repo1")
    assert diag_syntax["error_type"] == "SyntaxError"
    assert "backend/app/router.py" in diag_syntax["target_file"]
    assert diag_syntax["failing_line"] == "45"

    # 4. AssertionError
    log_assert = "FAILED tests/test_endpoints.py::test_login - AssertionError: assert 401 == 200"
    diag_assert = diagnose_failure_from_log(log_assert, "Run unit tests", "test-org/repo1")
    assert diag_assert["error_type"] == "AssertionError"
    assert "tests/test_endpoints.py" in diag_assert["target_file"]
    assert "assert 401 == 200" in diag_assert["root_cause"]

def test_validate_unified_diff_format():
    """Verify strict validation of unified diff syntax and rejection of invalid formats."""
    # 1. Authentic unified diff
    valid_diff = (
        "--- a/requirements.txt\n"
        "+++ b/requirements.txt\n"
        "@@ -1,3 +1,4 @@\n"
        " fastapi>=0.110.0\n"
        " pydantic>=2.5.0\n"
        "+httpx>=0.27.0\n"
        " uvicorn>=0.28.0\n"
    )
    is_valid, msg = validate_unified_diff(valid_diff)
    assert is_valid is True
    assert "Valid" in msg

    # 2. Missing '--- a/'
    invalid_no_orig = (
        "+++ b/requirements.txt\n"
        "@@ -1,3 +1,4 @@\n"
        "+httpx>=0.27.0\n"
    )
    is_valid, err = validate_unified_diff(invalid_no_orig)
    assert is_valid is False
    assert "Missing origin header" in err

    # 3. Missing '+++ b/'
    invalid_no_dest = (
        "--- a/requirements.txt\n"
        "@@ -1,3 +1,4 @@\n"
        "+httpx>=0.27.0\n"
    )
    is_valid, err = validate_unified_diff(invalid_no_dest)
    assert is_valid is False
    assert "Missing destination header" in err

    # 4. Missing hunk header
    invalid_no_hunk = (
        "--- a/requirements.txt\n"
        "+++ b/requirements.txt\n"
        "+httpx>=0.27.0\n"
    )
    is_valid, err = validate_unified_diff(invalid_no_hunk)
    assert is_valid is False
    assert "Missing hunk header" in err

    # 5. Empty or plain text without changes
    is_valid, err = validate_unified_diff("Just regular explanation text")
    assert is_valid is False

def test_verify_patch_in_sandbox_checks():
    """Verify isolated scratch sandbox validates syntax and catches malformed code."""
    # 1. Valid Python patch compiles cleanly in sandbox
    valid_py = [
        {"path": "app/core/helper.py", "content": "def calculate_total(a: int, b: int) -> int:\n    return a + b\n"}
    ]
    res_valid = verify_patch_in_sandbox(valid_py)
    assert res_valid["verified"] is True
    assert res_valid["status"] == "PASSED"
    assert "AST/syntax checks passed" in res_valid["details"]

    # 2. Python syntax error caught and blocked
    broken_py = [
        {"path": "app/broken.py", "content": "def syntax_error(\n    bad indent"}
    ]
    res_broken = verify_patch_in_sandbox(broken_py)
    assert res_broken["verified"] is False
    assert res_broken["status"] == "SYNTAX_ERROR"
    assert "Syntax error" in res_broken["error"]

    # 3. Malicious shell character in requirements file caught and blocked
    malicious_req = [
        {"path": "requirements.txt", "content": "fastapi>=0.110.0\npydantic; rm -rf /\n"}
    ]
    res_mal = verify_patch_in_sandbox(malicious_req)
    assert res_mal["verified"] is False
    assert res_mal["status"] == "SYNTAX_ERROR"
    assert "Invalid shell character" in res_mal["error"]

    # 4. Valid requirements file passes cleanly
    clean_req = [
        {"path": "requirements.txt", "content": "fastapi>=0.110.0\npydantic>=2.5.0\nhttpx>=0.27.0\n"}
    ]
    res_clean = verify_patch_in_sandbox(clean_req)
    assert res_clean["verified"] is True
    assert res_clean["status"] == "PASSED"

@pytest.mark.asyncio
async def test_end_to_end_grounded_analysis_and_sandbox_verified_proposal(monkeypatch):
    """
    Test end-to-end:
    1. Workflow failure with specific error log
    2. Analyze failure -> grounds root cause in log
    3. Propose fix -> runs sandbox verification, validates diff syntax, generates approval request
    """
    monkeypatch.setenv("MOCK_MODE", "true")
    await init_system_db()
    transport = ASGITransport(app=app)

    unique_run_id = 77112233
    failure_id = f"wf-phase5-{uuid.uuid4().hex[:8]}"
    custom_log = (
        "Traceback (most recent call last):\n"
        "  File \"backend/app/main.py\", line 12, in <module>\n"
        "    import redis\n"
        "ModuleNotFoundError: No module named 'redis'\n"
        "Process completed with exit code 1."
    )

    approval_id = None
    try:
        # 1. Seed specific workflow failure
        async with AsyncSessionLocal() as session:
            wf = WorkflowFailure(
                id=failure_id,
                workspace_id="default-ops",
                repo_full_name="adityabhagwat001/Opspilot1",
                workflow_name="CI Integration Suite",
                run_id=unique_run_id,
                commit_sha="c0ffee1234567890abcdef1234567890abcdef12",
                commit_message="feat: add redis cache client",
                head_branch="feature/caching",
                actor="devops-engineer",
                html_url=f"https://github.com/adityabhagwat001/Opspilot1/actions/runs/{unique_run_id}",
                failing_step="Run Integration Tests",
                error_log_snippet=custom_log,
                status="detected"
            )
            session.add(wf)
            await session.commit()

        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # 2. Analyze failure
            an_resp = await client.post(f"/api/github/failures/{failure_id}/analyze", headers=ADMIN_HEADERS)
            assert an_resp.status_code == 200
            an_data = an_resp.json()
            assert an_data["status"] == "SUCCESS"
            # Diagnosis must be grounded in 'redis', not generic 'pydantic'
            assert "redis" in an_data["root_cause"]

            # 3. Propose fix with sandbox verification
            prop_resp = await client.post(f"/api/github/failures/{failure_id}/propose-fix", headers=ADMIN_HEADERS)
            assert prop_resp.status_code == 200
            prop_data = prop_resp.json()
            assert prop_data["status"] == "SUCCESS"
            assert prop_data["sandbox_verified"] is True
            assert "AST/syntax checks passed" in prop_data["sandbox_test_result"]
            assert prop_data["approval_required"] is True
            assert prop_data["approval_id"] is not None
            approval_id = prop_data["approval_id"]

            # Verify diff content conforms to unified diff
            diff_text = prop_data["diff_content"]
            is_valid, _ = validate_unified_diff(diff_text)
            assert is_valid is True
            assert "redis" in diff_text

            # Verify approval request has sandbox verification badge
            async with AsyncSessionLocal() as session:
                appr = (await session.execute(select(ApprovalRequest).where(ApprovalRequest.id == approval_id))).scalar_one_or_none()
                assert appr is not None
                assert appr.target_system == "github"
                assert appr.tool_name == "create_pull_request"
                assert "redis" in appr.canonical_action_arguments
    finally:
        # Guaranteed teardown
        async with AsyncSessionLocal() as session:
            prop = (await session.execute(select(FixProposal).where(FixProposal.failure_id == failure_id))).scalar_one_or_none()
            if prop:
                await session.delete(prop)
            if approval_id:
                appr = (await session.execute(select(ApprovalRequest).where(ApprovalRequest.id == approval_id))).scalar_one_or_none()
                if appr:
                    await session.delete(appr)
            wf_del = (await session.execute(select(WorkflowFailure).where(WorkflowFailure.id == failure_id))).scalar_one_or_none()
            if wf_del:
                await session.delete(wf_del)
            await session.commit()
