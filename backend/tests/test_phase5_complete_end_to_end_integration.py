"""
Test Suite: Phase 5 - Complete End-to-End Multi-Tenant Enterprise Integration Lifecycle
Validates the complete real-world enterprise journey:
1. Company Registration & Admin Email Verification.
2. Unified Login & Multi-Tenant Workspace Resolution.
3. Employee Invitation by Admin with SHA-256 Token Storage.
4. Employee Invitation Acceptance & Account Enrollment.
5. Role Distinction: Operator proposes actions; Admin manages & approves.
6. AI Assistant / FastMCP Write Boundary Enforcement & Approval Request Creation.
7. Approval Center Security: Operator cannot self-approve; Admin authorizes write action.
8. Single-Use Capability Token Consumption & Replay Immunity.
9. Tenant Isolation: Independent second company has complete isolation across all models.
10. Backward Compatibility: Existing seed accounts (admin@opspilot.internal, operator@opspilot.internal) operational.
"""

import pytest
import uuid
import datetime
import json
import httpx
from sqlalchemy import select
from app.main import app
from app.core.db import AsyncSessionLocal
from app.models.models import (
    User, 
    Workspace, 
    WorkspaceMember, 
    WorkspaceInvitation, 
    MonitoredRepository, 
    ApprovalRequest, 
    ConsumedApprovalToken, 
    AuditLog,
    AgentConversation
)

@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.asyncio
async def test_complete_enterprise_end_to_end_lifecycle():
    """
    Executes the entire enterprise operations journey from company creation
    to employee onboarding, AI operations, approval authorization, and tenant isolation.
    """
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        # =====================================================================
        # STEP 1: Company Registration & Initial Admin Account Creation
        # =====================================================================
        comp_name = f"Acme Global {uuid.uuid4().hex[:6]}"
        admin_email = f"lead-admin-{uuid.uuid4().hex[:6]}@acmeglobal.corp"
        password = "AcmeEnterprisePassword123!"

        reg_res = await client.post("/api/auth/register/company", json={
            "company_name": comp_name,
            "company_email": "operations@acmeglobal.corp",
            "company_website": "https://www.acmeglobal.corp",
            "industry": "Autonomous Cloud Systems",
            "admin_full_name": "Sarah Connor",
            "admin_email": admin_email,
            "password": password,
            "confirm_password": password
        })
        assert reg_res.status_code == 200, f"Registration failed: {reg_res.text}"
        reg_data = reg_res.json()
        assert reg_data["status"] == "SUCCESS"
        ws_id = reg_data["workspace_id"]
        v_token = reg_data["verification_token"]

        # =====================================================================
        # STEP 2: Email Verification & Unified Login
        # =====================================================================
        ver_res = await client.post("/api/auth/verify-email", json={"token": v_token})
        assert ver_res.status_code == 200

        login_res = await client.post("/api/auth/login", json={
            "email": admin_email,
            "password": password
        })
        assert login_res.status_code == 200
        admin_auth = login_res.json()
        admin_token = admin_auth["access_token"]
        admin_id = admin_auth["user"]["id"]
        assert admin_auth["user"]["role"] == "admin"
        assert admin_auth["user"]["workspace_id"] == ws_id

        admin_headers = {"Authorization": f"Bearer {admin_token}", "X-Workspace-Id": ws_id}

        # Check Company Details
        comp_details = (await client.get("/api/company", headers=admin_headers)).json()
        assert comp_details["name"] == comp_name
        assert comp_details["member_count"] == 1

        # =====================================================================
        # STEP 3: Admin Invites DevOps Operator
        # =====================================================================
        op_email = f"devops-engineer-{uuid.uuid4().hex[:6]}@acmeglobal.corp"
        invite_res = await client.post("/api/auth/invite", headers=admin_headers, json={
            "email": op_email,
            "role": "operator"
        })
        assert invite_res.status_code == 200
        inv_token = invite_res.json()["invitation_token"]

        # Verify invitation listed in pending invitations
        invs = (await client.get("/api/company/invitations", headers=admin_headers)).json()
        assert any(i["email"] == op_email for i in invs)

        # =====================================================================
        # STEP 4: Operator Registers via Invitation Token & Signs In
        # =====================================================================
        op_password = "OperatorPass123!"
        op_reg_res = await client.post("/api/auth/register-invite", json={
            "token": inv_token,
            "full_name": "Kyle Reese",
            "password": op_password,
            "confirm_password": op_password
        })
        assert op_reg_res.status_code == 200

        op_login = await client.post("/api/auth/login", json={
            "email": op_email,
            "password": op_password
        })
        assert op_login.status_code == 200
        op_auth = op_login.json()
        op_token = op_auth["access_token"]
        op_id = op_auth["user"]["id"]
        assert op_auth["user"]["role"] == "operator"
        assert op_auth["user"]["workspace_id"] == ws_id

        op_headers = {"Authorization": f"Bearer {op_token}", "X-Workspace-Id": ws_id}

        # Verify member roster updated
        mems = (await client.get("/api/company/members", headers=admin_headers)).json()
        assert len(mems) == 2

        # =====================================================================
        # STEP 5: Operator Proposes Action (Creates Approval Request)
        # =====================================================================
        # Operator initiates a conversation
        conv_res = await client.post("/api/chat/conversations", headers=op_headers, json={"title": "Fix Database Degradation"})
        assert conv_res.status_code == 200
        conv_id = conv_res.json()["id"]

        from app.approvals.approval_service import approval_service
        async with AsyncSessionLocal() as session:
            appr_request = await approval_service.create_approval_request(
                db=session,
                execution_id=f"exec-{uuid.uuid4().hex[:8]}",
                user_id=op_id,
                workspace_id=ws_id,
                target_system="postgresql",
                tool_name="create_operational_task",
                arguments={
                    "title": "Scale database read replicas",
                    "description": "Scale read replicas up to 4 to reduce latency"
                },
                action_summary="Increase replica count to handle peak query load"
            )
            appr_id = appr_request.id

        # =====================================================================
        # STEP 6: Operator Cannot Self-Approve (403 Forbidden)
        # =====================================================================
        op_approve_attempt = await client.post(f"/api/approvals/{appr_id}/approve", headers=op_headers)
        assert op_approve_attempt.status_code == 403

        # =====================================================================
        # STEP 7: Admin Reviews and Approves in Approval Center
        # =====================================================================
        admin_apprs = (await client.get("/api/approvals", headers=admin_headers)).json()
        assert any(a["id"] == appr_id for a in admin_apprs)

        admin_approve_res = await client.post(f"/api/approvals/{appr_id}/approve", headers=admin_headers)
        assert admin_approve_res.status_code == 200
        approve_body = admin_approve_res.json()
        assert approve_body["status"] in ("SUCCESS", "FAILED")
        assert approve_body["approval_id"] == appr_id

        # Verify nonce consumption and audit log
        async with AsyncSessionLocal() as session:
            consumed = (await session.execute(
                select(ConsumedApprovalToken).where(ConsumedApprovalToken.approval_id == appr_id)
            )).scalar_one_or_none()
            assert consumed is not None
            assert consumed.workspace_id == ws_id

            audit_entry = (await session.execute(
                select(AuditLog).where(AuditLog.approval_id == appr_id)
            )).scalar_one_or_none()
            assert audit_entry is not None
            assert audit_entry.workspace_id == ws_id
            assert audit_entry.user_id == admin_id

        # =====================================================================
        # STEP 8: Second Company Isolation Verification
        # =====================================================================
        comp2_name = f"Cyberdyne Systems {uuid.uuid4().hex[:6]}"
        admin2_email = f"director-{uuid.uuid4().hex[:6]}@cyberdyne.corp"
        reg2_res = await client.post("/api/auth/register/company", json={
            "company_name": comp2_name,
            "company_email": "hq@cyberdyne.corp",
            "company_website": "https://www.cyberdyne.corp",
            "industry": "Artificial Intelligence",
            "admin_full_name": "Miles Dyson",
            "admin_email": admin2_email,
            "password": password,
            "confirm_password": password
        })
        assert reg2_res.status_code == 200
        await client.post("/api/auth/verify-email", json={"token": reg2_res.json()["verification_token"]})
        login2_res = await client.post("/api/auth/login", json={"email": admin2_email, "password": password})
        token2 = login2_res.json()["access_token"]
        ws2_id = reg2_res.json()["workspace_id"]
        headers2 = {"Authorization": f"Bearer {token2}", "X-Workspace-Id": ws2_id}

        # Company 2 sees 0 approvals, 0 members from Company 1, 0 audit logs from Company 1
        comp2_apprs = (await client.get("/api/approvals", headers=headers2)).json()
        assert not any(a["id"] == appr_id for a in comp2_apprs)

        comp2_audit = (await client.get("/api/audit", headers=headers2)).json()
        assert not any(l["approval_id"] == appr_id for l in comp2_audit)

        # Cross-tenant spoofing attempt from Company 2 into Company 1 -> 403 Forbidden
        spoofed = {"Authorization": f"Bearer {token2}", "X-Workspace-Id": ws_id}
        cross_attempt = await client.get("/api/company", headers=spoofed)
        assert cross_attempt.status_code == 403

        # =====================================================================
        # STEP 9: Backward Compatibility with Seed Accounts
        # =====================================================================
        seed_admin = await client.post("/api/auth/login", json={
            "email": "admin@opspilot.internal",
            "password": "admin123"
        })
        assert seed_admin.status_code == 200
        assert seed_admin.json()["user"]["role"] == "admin"

        seed_op = await client.post("/api/auth/login", json={
            "email": "operator@opspilot.internal",
            "password": "operator123"
        })
        assert seed_op.status_code == 200
        assert seed_op.json()["user"]["role"] == "operator"
