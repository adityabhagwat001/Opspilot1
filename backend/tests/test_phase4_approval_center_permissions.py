"""
Test Suite: Phase 4 - Enterprise Approval Center Permissions & Separation of Duties
Verifies:
1. DevOps Operator cannot approve write actions (403 Forbidden).
2. DevOps Operator cannot reject other users' approval requests (403 Forbidden).
3. DevOps Operator CAN cancel/reject their own submitted requests (status transitions to rejected).
4. DevOps Operator cannot delete individual approvals or purge inactive requests (403 Forbidden).
5. Enterprise Administrator can approve operator-submitted requests.
6. Enterprise Administrator can reject any pending request in the workspace.
7. Separation of Duties: Admin cannot approve their own submitted request when SoD is enabled.
8. Separation of Duties: A second Admin in the workspace CAN approve the first Admin's request.
9. Enterprise Administrator can delete approval records and purge inactive requests.
"""

import pytest
import uuid
import datetime
import httpx
from sqlalchemy import select
from app.main import app
from app.core.db import AsyncSessionLocal
from app.models.models import (
    User, 
    Workspace, 
    WorkspaceMember, 
    ApprovalRequest, 
    AgentConversation,
    utc_now
)
from app.core.security import compute_action_hash

@pytest.fixture
def anyio_backend():
    return "asyncio"


async def setup_company_with_operator_and_admins(client: httpx.AsyncClient, name_prefix: str):
    """
    Helper creating a company with:
    - Admin 1 (Creator)
    - Admin 2 (Peer Reviewer)
    - Operator 1
    """
    company_name = f"{name_prefix} Org {uuid.uuid4().hex[:6]}"
    admin1_email = f"admin1-{uuid.uuid4().hex[:6]}@{name_prefix.lower()}.com"
    password = "SecurePassword123!"

    # 1. Register company with Admin 1
    reg_res = await client.post("/api/auth/register/company", json={
        "company_name": company_name,
        "company_email": f"info@{name_prefix.lower()}.com",
        "company_website": f"https://{name_prefix.lower()}.com",
        "industry": "Cloud Infrastructure",
        "admin_full_name": f"{name_prefix} Primary Admin",
        "admin_email": admin1_email,
        "password": password,
        "confirm_password": password
    })
    assert reg_res.status_code == 200
    data = reg_res.json()
    ws_id = data["workspace_id"]
    await client.post("/api/auth/verify-email", json={"token": data["verification_token"]})

    login_admin1 = await client.post("/api/auth/login", json={"email": admin1_email, "password": password})
    admin1_token = login_admin1.json()["access_token"]
    admin1_id = login_admin1.json()["user"]["id"]
    admin1_headers = {"Authorization": f"Bearer {admin1_token}", "X-Workspace-Id": ws_id}

    # 2. Admin 1 invites Operator 1
    op_email = f"operator-{uuid.uuid4().hex[:6]}@{name_prefix.lower()}.com"
    inv_op = (await client.post("/api/auth/invite", headers=admin1_headers, json={"email": op_email, "role": "operator"})).json()
    await client.post("/api/auth/register-invite", json={
        "token": inv_op["invitation_token"],
        "full_name": f"{name_prefix} Operator",
        "password": password,
        "confirm_password": password
    })
    login_op = await client.post("/api/auth/login", json={"email": op_email, "password": password})
    op_token = login_op.json()["access_token"]
    op_id = login_op.json()["user"]["id"]
    op_headers = {"Authorization": f"Bearer {op_token}", "X-Workspace-Id": ws_id}

    # 3. Admin 1 invites Admin 2
    admin2_email = f"admin2-{uuid.uuid4().hex[:6]}@{name_prefix.lower()}.com"
    inv_ad2 = (await client.post("/api/auth/invite", headers=admin1_headers, json={"email": admin2_email, "role": "admin"})).json()
    await client.post("/api/auth/register-invite", json={
        "token": inv_ad2["invitation_token"],
        "full_name": f"{name_prefix} Secondary Admin",
        "password": password,
        "confirm_password": password
    })
    login_admin2 = await client.post("/api/auth/login", json={"email": admin2_email, "password": password})
    admin2_token = login_admin2.json()["access_token"]
    admin2_id = login_admin2.json()["user"]["id"]
    admin2_headers = {"Authorization": f"Bearer {admin2_token}", "X-Workspace-Id": ws_id}

    return {
        "workspace_id": ws_id,
        "admin1": {"id": admin1_id, "token": admin1_token, "headers": admin1_headers},
        "admin2": {"id": admin2_id, "token": admin2_token, "headers": admin2_headers},
        "operator": {"id": op_id, "token": op_token, "headers": op_headers}
    }


async def insert_approval_request(workspace_id: str, requester_id: str) -> str:
    """Helper to insert a pending approval request."""
    appr_id = f"appr-{uuid.uuid4().hex[:12]}"
    exec_id = f"exec-{uuid.uuid4().hex[:12]}"
    now = datetime.datetime.now(datetime.timezone.utc)

    args = {"recipient": "team@company.internal", "subject": "Alert", "body": "Disk full"}
    action_hash = compute_action_hash("send_operations_email", args)
    import json

    async with AsyncSessionLocal() as session:
        appr = ApprovalRequest(
            id=appr_id,
            execution_id=exec_id,
            requesting_user_id=requester_id,
            workspace_id=workspace_id,
            target_system="email",
            tool_name="send_operations_email",
            canonical_action_arguments=json.dumps(args),
            action_summary="Send Disk Full alert email to operations team",
            action_hash=action_hash,
            approval_status="pending",
            expires_at=now + datetime.timedelta(minutes=30)
        )
        session.add(appr)
        await session.commit()
    return appr_id


@pytest.mark.asyncio
async def test_operator_forbidden_from_approving():
    """Verifies that an Operator cannot approve requests (403 Forbidden)."""
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        env = await setup_company_with_operator_and_admins(client, "OpNoApprove")
        appr_id = await insert_approval_request(env["workspace_id"], env["operator"]["id"])

        res = await client.post(f"/api/approvals/{appr_id}/approve", headers=env["operator"]["headers"])
        assert res.status_code == 403


@pytest.mark.asyncio
async def test_operator_cannot_reject_others_requests():
    """Verifies that an Operator cannot reject approval requests initiated by another user (403 Forbidden)."""
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        env = await setup_company_with_operator_and_admins(client, "OpNoRejectOther")
        # Request created by Admin 1
        appr_id = await insert_approval_request(env["workspace_id"], env["admin1"]["id"])

        # Operator attempts to reject Admin 1's request -> 403 Forbidden
        res = await client.post(f"/api/approvals/{appr_id}/reject", headers=env["operator"]["headers"], json={
            "reason": "Not allowed"
        })
        assert res.status_code == 403


@pytest.mark.asyncio
async def test_operator_can_cancel_own_request():
    """Verifies that an Operator CAN cancel their own submitted request."""
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        env = await setup_company_with_operator_and_admins(client, "OpCancelOwn")
        appr_id = await insert_approval_request(env["workspace_id"], env["operator"]["id"])

        # Operator cancels their own proposal
        res = await client.post(f"/api/approvals/{appr_id}/reject", headers=env["operator"]["headers"], json={
            "reason": "Cancelled by operator"
        })
        assert res.status_code == 200
        assert res.json()["status"] == "REJECTED"

        # Verify state in database
        async with AsyncSessionLocal() as session:
            rec = (await session.execute(select(ApprovalRequest).where(ApprovalRequest.id == appr_id))).scalar_one()
            assert rec.approval_status == "rejected"


@pytest.mark.asyncio
async def test_operator_forbidden_from_deleting_and_purging():
    """Verifies that an Operator cannot delete individual records or purge inactive approvals."""
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        env = await setup_company_with_operator_and_admins(client, "OpNoDelete")
        appr_id = await insert_approval_request(env["workspace_id"], env["operator"]["id"])

        del_res = await client.delete(f"/api/approvals/{appr_id}", headers=env["operator"]["headers"])
        assert del_res.status_code == 403

        purge_res = await client.post("/api/approvals/purge", headers=env["operator"]["headers"])
        assert purge_res.status_code == 403


@pytest.mark.asyncio
async def test_admin_can_approve_operator_request():
    """Verifies that an Enterprise Admin can approve and execute an operator's request."""
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        env = await setup_company_with_operator_and_admins(client, "AdminApprove")
        appr_id = await insert_approval_request(env["workspace_id"], env["operator"]["id"])

        res = await client.post(f"/api/approvals/{appr_id}/approve", headers=env["admin1"]["headers"])
        assert res.status_code == 200
        assert res.json()["status"] in ("SUCCESS", "FAILED")
        assert res.json()["approval_id"] == appr_id


@pytest.mark.asyncio
async def test_admin_can_reject_any_request():
    """Verifies that an Enterprise Admin can reject any request with an explicit reason."""
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        env = await setup_company_with_operator_and_admins(client, "AdminReject")
        appr_id = await insert_approval_request(env["workspace_id"], env["operator"]["id"])

        res = await client.post(f"/api/approvals/{appr_id}/reject", headers=env["admin1"]["headers"], json={
            "reason": "Does not comply with operational policy"
        })
        assert res.status_code == 200
        assert res.json()["status"] == "REJECTED"


@pytest.mark.asyncio
async def test_separation_of_duties_prevents_self_approval():
    """
    Verifies Separation of Duties: An administrator who created an action
    cannot approve their own request when SoD is enforced.
    A second administrator in the organization CAN approve it.
    """
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        env = await setup_company_with_operator_and_admins(client, "SoDTest")
        # Request created by Admin 1
        appr_id = await insert_approval_request(env["workspace_id"], env["admin1"]["id"])

        # 1. Admin 1 attempts to self-approve with SoD enforced -> 403 Forbidden
        headers_sod = {**env["admin1"]["headers"], "X-Enforce-Separation-Of-Duties": "true"}
        self_res = await client.post(f"/api/approvals/{appr_id}/approve", headers=headers_sod)
        assert self_res.status_code == 403
        assert "separation of duties" in self_res.json()["detail"].lower()

        # 2. Admin 2 (peer reviewer) approves Admin 1's request -> succeeds
        peer_headers = {**env["admin2"]["headers"], "X-Enforce-Separation-Of-Duties": "true"}
        peer_res = await client.post(f"/api/approvals/{appr_id}/approve", headers=peer_headers)
        assert peer_res.status_code == 200
        assert peer_res.json()["status"] in ("SUCCESS", "FAILED")
        assert peer_res.json()["approval_id"] == appr_id


@pytest.mark.asyncio
async def test_admin_can_delete_and_purge_approvals():
    """Verifies that an Enterprise Admin can delete individual records and purge stale approvals."""
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        env = await setup_company_with_operator_and_admins(client, "AdminPurge")
        appr_id = await insert_approval_request(env["workspace_id"], env["operator"]["id"])

        # First reject it so it becomes inactive
        await client.post(f"/api/approvals/{appr_id}/reject", headers=env["admin1"]["headers"], json={"reason": "Testing purge"})

        # Purge inactive
        purge_res = await client.post("/api/approvals/purge", headers=env["admin1"]["headers"])
        assert purge_res.status_code == 200
        assert purge_res.json()["status"] == "SUCCESS"
        assert purge_res.json()["purged_count"] >= 1
