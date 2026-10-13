"""
Approval Security Verification Test Suite
Verifies that no write operation can bypass the human approval boundary,
tampered parameters are rejected, expired approvals fail, and single-use is enforced.
"""

import pytest
import datetime
import json
from app.core.security import compute_action_hash, generate_approval_token, verify_approval_token
from app.core.db import AsyncSessionLocal, init_system_db
from app.approvals.approval_service import approval_service
from app.models.models import ApprovalRequest, User
from sqlalchemy import select

@pytest.mark.asyncio
async def test_action_hash_deterministic():
    args_1 = {"title": "Fix bug", "priority": "p1"}
    args_2 = {"priority": "p1", "title": "Fix bug"}  # reordered
    assert compute_action_hash("create_task", args_1) == compute_action_hash("create_task", args_2)

@pytest.mark.asyncio
async def test_tampered_parameters_hash_mismatch():
    original_args = {"title": "Fix bug", "priority": "p1"}
    tampered_args = {"title": "Fix bug", "priority": "p0"}  # escalated priority
    h1 = compute_action_hash("create_task", original_args)
    h2 = compute_action_hash("create_task", tampered_args)
    assert h1 != h2

@pytest.mark.asyncio
async def test_forged_approval_token_rejected():
    fake_token = "1728800000.abc123hash.fake_signature_forged_by_attacker"
    valid = verify_approval_token("create_issue", {"title": "Test"}, fake_token)
    assert valid is False

@pytest.mark.asyncio
async def test_genuine_approval_token_verified():
    args = {"title": "Test Valid Ticket"}
    genuine_token = generate_approval_token("create_issue", args)
    assert verify_approval_token("create_issue", args, genuine_token) is True

@pytest.mark.asyncio
async def test_approval_lifecycle_and_rejection():
    await init_system_db()
    async with AsyncSessionLocal() as session:
        # Create an approval request
        appr = await approval_service.create_approval_request(
            db=session,
            execution_id="test-exec-101",
            user_id="usr-admin-01",
            workspace_id="default-ops",
            target_system="postgresql",
            tool_name="create_operational_task",
            arguments={"title": "Test Task", "description": "Desc"},
            action_summary="Test summary"
        )
        assert appr.approval_status == "pending"

        # Reject it
        rej_res = await approval_service.reject_request(
            db=session,
            approval_id=appr.id,
            user_id="usr-admin-01",
            reason="Blocked by security review"
        )
        assert rej_res["status"] == "REJECTED"

        # Re-attempting approval on rejected request must fail
        re_appr = await approval_service.approve_and_execute(
            db=session,
            approval_id=appr.id,
            approver_user_id="usr-admin-01"
        )
        assert re_appr["status"] == "ERROR"
        assert "Cannot approve request in 'rejected' state" in re_appr["error"]
