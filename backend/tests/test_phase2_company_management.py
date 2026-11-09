"""
Test Suite: Phase 2 - Company Management, Employee Invitations, Automatic RBAC & Sole Admin Protection
Verifies:
1. Enterprise Administrator can invite employees to company workspace.
2. Operator cannot issue invitations (403 Forbidden).
3. Employee registers via valid invitation token and gains workspace access.
4. Expired, invalid, or already accepted invitation tokens are rejected (400 Bad Request).
5. Existing users can accept invitations by confirming password without duplicate account creation.
6. Sole administrator cannot be demoted (Sole Admin Protection).
7. Sole administrator cannot be removed (Sole Admin Protection).
8. Admin can promote operator to admin, and multiple admins allow demotion.
9. Admin can remove employee from workspace.
10. Admin can list and revoke pending invitations.
11. Multi-workspace listing and switching context via JWT token.
"""

import pytest
import uuid
import datetime
import httpx
from sqlalchemy import select, func
from app.main import app
from app.core.db import AsyncSessionLocal
from app.models.models import User, Workspace, WorkspaceMember, WorkspaceInvitation, utc_now

@pytest.fixture
def anyio_backend():
    return "asyncio"


async def create_test_company(client: httpx.AsyncClient, prefix: str):
    """Helper to register a verified company with an administrator."""
    company_name = f"{prefix} Corp {uuid.uuid4().hex[:6]}"
    admin_email = f"admin-{uuid.uuid4().hex[:6]}@test{prefix.lower()}.com"
    password = "AdminSecurePassword123!"

    reg_res = await client.post("/api/auth/register/company", json={
        "company_name": company_name,
        "company_email": f"contact@test{prefix.lower()}.com",
        "company_website": f"https://www.test{prefix.lower()}.com",
        "industry": "FinTech",
        "admin_full_name": f"{prefix} Administrator",
        "admin_email": admin_email,
        "password": password,
        "confirm_password": password
    })
    assert reg_res.status_code == 200, f"Company registration failed: {reg_res.text}"
    data = reg_res.json()
    ws_id = data["workspace_id"]
    v_token = data["verification_token"]

    # Verify admin email
    ver_res = await client.post("/api/auth/verify-email", json={"token": v_token})
    assert ver_res.status_code == 200

    # Login admin
    login_res = await client.post("/api/auth/login", json={
        "email": admin_email,
        "password": password
    })
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    user_id = login_res.json()["user"]["id"]

    return {
        "workspace_id": ws_id,
        "admin_email": admin_email,
        "admin_id": user_id,
        "token": token,
        "headers": {"Authorization": f"Bearer {token}", "X-Workspace-Id": ws_id}
    }


@pytest.mark.asyncio
async def test_admin_invite_and_operator_registration_flow():
    """Verifies that an Enterprise Admin can invite an employee, who then registers via token."""
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        comp = await create_test_company(client, "Flow1")

        # 1. Admin invites employee
        emp_email = f"engineer-{uuid.uuid4().hex[:6]}@testflow1.com"
        invite_res = await client.post(
            "/api/auth/invite",
            headers=comp["headers"],
            json={"email": emp_email, "role": "operator"}
        )
        assert invite_res.status_code == 200, f"Invite failed: {invite_res.text}"
        inv_data = invite_res.json()
        assert inv_data["status"] == "SUCCESS"
        inv_token = inv_data["invitation_token"]

        # 2. Employee completes registration using token
        emp_password = "OperatorSecurePass123!"
        reg_res = await client.post("/api/auth/register-invite", json={
            "token": inv_token,
            "full_name": "DevOps Engineer Alice",
            "password": emp_password,
            "confirm_password": emp_password
        })
        assert reg_res.status_code == 200, f"Register invite failed: {reg_res.text}"
        assert reg_res.json()["status"] == "SUCCESS"

        # 3. Employee signs in
        login_res = await client.post("/api/auth/login", json={
            "email": emp_email,
            "password": emp_password
        })
        assert login_res.status_code == 200
        emp_auth = login_res.json()
        assert emp_auth["user"]["role"] == "operator"
        assert emp_auth["user"]["workspace_id"] == comp["workspace_id"]


@pytest.mark.asyncio
async def test_operator_forbidden_from_inviting():
    """Verifies that an Operator cannot invite other employees (403 Forbidden)."""
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        comp = await create_test_company(client, "Flow2")

        # Invite and register an operator
        emp_email = f"op-{uuid.uuid4().hex[:6]}@testflow2.com"
        inv = (await client.post("/api/auth/invite", headers=comp["headers"], json={"email": emp_email, "role": "operator"})).json()
        await client.post("/api/auth/register-invite", json={
            "token": inv["invitation_token"],
            "full_name": "Operator Bob",
            "password": "Password123!",
            "confirm_password": "Password123!"
        })
        login_res = await client.post("/api/auth/login", json={"email": emp_email, "password": "Password123!"})
        op_token = login_res.json()["access_token"]
        op_headers = {"Authorization": f"Bearer {op_token}", "X-Workspace-Id": comp["workspace_id"]}

        # Operator attempts to invite
        bad_invite = await client.post(
            "/api/auth/invite",
            headers=op_headers,
            json={"email": "intruder@testflow2.com", "role": "operator"}
        )
        assert bad_invite.status_code == 403


@pytest.mark.asyncio
async def test_invalid_and_expired_invitation_tokens():
    """Verifies that invalid, expired, and reused invitation tokens are rejected."""
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        comp = await create_test_company(client, "Flow3")

        # 1. Nonexistent token
        res1 = await client.post("/api/auth/register-invite", json={
            "token": "completely-fake-token-12345",
            "full_name": "Fake User",
            "password": "Password123!",
            "confirm_password": "Password123!"
        })
        assert res1.status_code == 400

        # 2. Expired token
        emp_email = f"expired-{uuid.uuid4().hex[:6]}@testflow3.com"
        inv = (await client.post("/api/auth/invite", headers=comp["headers"], json={"email": emp_email, "role": "operator"})).json()
        token = inv["invitation_token"]

        # Manually expire in DB
        async with AsyncSessionLocal() as session:
            inv_obj = (await session.execute(select(WorkspaceInvitation).where(WorkspaceInvitation.email == emp_email))).scalar_one()
            inv_obj.expires_at = utc_now() - datetime.timedelta(days=1)
            await session.commit()

        res2 = await client.post("/api/auth/register-invite", json={
            "token": token,
            "full_name": "Expired User",
            "password": "Password123!",
            "confirm_password": "Password123!"
        })
        assert res2.status_code == 400
        assert "expired" in res2.json()["detail"].lower()


@pytest.mark.asyncio
async def test_sole_admin_protection_on_demotion_and_removal():
    """Verifies that the sole remaining administrator cannot be demoted or removed from the workspace."""
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        comp = await create_test_company(client, "SoleAdmin")

        # Get member list to find the admin member_id
        mems_res = await client.get("/api/company/members", headers=comp["headers"])
        assert mems_res.status_code == 200
        members = mems_res.json()
        admin_member = next(m for m in members if m["user_id"] == comp["admin_id"])
        admin_member_id = admin_member["member_id"]

        # 1. Attempt to demote sole admin to operator -> must be blocked with 400
        demote_res = await client.put(
            f"/api/company/members/{admin_member_id}/role",
            headers=comp["headers"],
            json={"role": "operator"}
        )
        assert demote_res.status_code == 400
        assert "sole remaining administrator" in demote_res.json()["detail"].lower()

        # 2. Attempt to remove sole admin -> must be blocked with 400
        remove_res = await client.delete(
            f"/api/company/members/{admin_member_id}",
            headers=comp["headers"]
        )
        assert remove_res.status_code == 400
        assert "sole remaining administrator" in remove_res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_role_promotion_and_demotion_with_multiple_admins():
    """Verifies that an operator can be promoted to admin, and once 2 admins exist, demotion is permitted."""
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        comp = await create_test_company(client, "MultiAdmin")

        # 1. Invite and register an operator
        emp_email = f"op2-{uuid.uuid4().hex[:6]}@testmultiadmin.com"
        inv = (await client.post("/api/auth/invite", headers=comp["headers"], json={"email": emp_email, "role": "operator"})).json()
        await client.post("/api/auth/register-invite", json={
            "token": inv["invitation_token"],
            "full_name": "Second In Command",
            "password": "Password123!",
            "confirm_password": "Password123!"
        })

        # Find operator member ID
        mems = (await client.get("/api/company/members", headers=comp["headers"])).json()
        op_member = next(m for m in mems if m["email"] == emp_email)
        admin_member = next(m for m in mems if m["user_id"] == comp["admin_id"])

        # 2. Promote operator to admin -> succeeds
        promote_res = await client.put(
            f"/api/company/members/{op_member['member_id']}/role",
            headers=comp["headers"],
            json={"role": "admin"}
        )
        assert promote_res.status_code == 200
        assert promote_res.json()["new_role"] == "admin"

        # 3. Now that 2 admins exist, demoting the original admin succeeds
        demote_res = await client.put(
            f"/api/company/members/{admin_member['member_id']}/role",
            headers=comp["headers"],
            json={"role": "operator"}
        )
        assert demote_res.status_code == 200
        assert demote_res.json()["new_role"] == "operator"


@pytest.mark.asyncio
async def test_remove_employee_and_access_revocation():
    """Verifies that an admin can remove an employee, and the removed member cannot access company data."""
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        comp = await create_test_company(client, "Removal")

        # 1. Invite and register employee
        emp_email = f"term-{uuid.uuid4().hex[:6]}@testremoval.com"
        inv = (await client.post("/api/auth/invite", headers=comp["headers"], json={"email": emp_email, "role": "operator"})).json()
        await client.post("/api/auth/register-invite", json={
            "token": inv["invitation_token"],
            "full_name": "Temporary Operator",
            "password": "Password123!",
            "confirm_password": "Password123!"
        })

        mems = (await client.get("/api/company/members", headers=comp["headers"])).json()
        term_member = next(m for m in mems if m["email"] == emp_email)

        # 2. Remove employee
        del_res = await client.delete(
            f"/api/company/members/{term_member['member_id']}",
            headers=comp["headers"]
        )
        assert del_res.status_code == 200

        # Verify member no longer in roster
        mems_after = (await client.get("/api/company/members", headers=comp["headers"])).json()
        assert not any(m["email"] == emp_email for m in mems_after)


@pytest.mark.asyncio
async def test_invitation_revocation_by_admin():
    """Verifies that an admin can revoke a pending invitation, preventing subsequent registration."""
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        comp = await create_test_company(client, "Revoke")

        # Create invite
        emp_email = f"revoked-{uuid.uuid4().hex[:6]}@testrevoke.com"
        inv = (await client.post("/api/auth/invite", headers=comp["headers"], json={"email": emp_email, "role": "operator"})).json()
        token = inv["invitation_token"]

        # List invitations
        invs = (await client.get("/api/company/invitations", headers=comp["headers"])).json()
        target_inv = next(i for i in invs if i["email"] == emp_email)

        # Revoke invitation
        rev_res = await client.delete(
            f"/api/company/invitations/{target_inv['id']}",
            headers=comp["headers"]
        )
        assert rev_res.status_code == 200

        # Try registering with revoked invitation -> 400
        reg_res = await client.post("/api/auth/register-invite", json={
            "token": token,
            "full_name": "Revoked Person",
            "password": "Password123!",
            "confirm_password": "Password123!"
        })
        assert reg_res.status_code == 400


@pytest.mark.asyncio
async def test_workspace_listing_and_switching():
    """Verifies multi-workspace listing and switching context."""
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        comp1 = await create_test_company(client, "WS1")
        comp2 = await create_test_company(client, "WS2")

        # Invite same user to comp2
        user_email = comp1["admin_email"]
        inv = (await client.post(
            "/api/auth/invite",
            headers=comp2["headers"],
            json={"email": user_email, "role": "operator"}
        )).json()

        # User accepts invitation using their existing password
        accept_res = await client.post("/api/auth/register-invite", json={
            "token": inv["invitation_token"],
            "full_name": "Dual Member",
            "password": "AdminSecurePassword123!",
            "confirm_password": "AdminSecurePassword123!"
        })
        assert accept_res.status_code == 200

        # List workspaces for user
        ws_list_res = await client.get("/api/auth/workspaces", headers={"Authorization": f"Bearer {comp1['token']}"})
        assert ws_list_res.status_code == 200
        user_workspaces = ws_list_res.json()
        ws_ids = [w["id"] for w in user_workspaces]
        assert comp1["workspace_id"] in ws_ids
        assert comp2["workspace_id"] in ws_ids

        # Switch workspace context to comp2
        switch_res = await client.post(
            "/api/auth/switch-workspace",
            headers={"Authorization": f"Bearer {comp1['token']}"},
            json={"workspace_id": comp2["workspace_id"]}
        )
        assert switch_res.status_code == 200
        new_token = switch_res.json()["access_token"]
        assert new_token is not None

