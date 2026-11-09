"""
OpsPilot Phase 6: Human Approval Verification End-to-End Test Suite
Verifies:
- End-to-end Approval Center REST lifecycle (create, query, approve, execute, reject, delete, purge)
- Single-use cryptographic nonce consumption into consumed_approval_tokens
- Replay attack defense: Reusing consumed nonces is blocked 100%
- Parameter tampering detection: Canonical arguments hash integrity verification
- 15-minute expiration window enforcement: Stale requests are automatically marked expired
- Cross-workspace isolation: Tenant A cannot inspect or approve Tenant B requests
- Double-approval race condition prevention via atomic status claiming
"""

import json
import uuid
import datetime
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.db import AsyncSessionLocal, init_system_db
from app.core.security import create_access_token, generate_approval_token, verify_approval_token, compute_action_hash
from app.models.models import ApprovalRequest, ConsumedApprovalToken, Workspace, WorkspaceMember, User
from app.approvals.approval_service import approval_service
from sqlalchemy import select, delete

ADMIN_HEADERS = {
    "Authorization": f"Bearer {create_access_token({'sub': 'usr-admin-01'})}"
}

OPERATOR_HEADERS = {
    "Authorization": f"Bearer {create_access_token({'sub': 'usr-operator-01'})}"
}

@pytest.mark.asyncio
async def test_end_to_end_approval_and_execution_lifecycle():
    """Verify approval creation, atomic approve_and_execute, nonce consumption, and double-approval prevention."""
    await init_system_db()
    transport = ASGITransport(app=app)
    
    # 1. Create a pending approval request
    req_args = {"title": "Scale workers", "description": "Scale background worker pool to 8 replicas"}
    async with AsyncSessionLocal() as session:
        appr = await approval_service.create_approval_request(
            db=session,
            execution_id=f"exec-p6-{uuid.uuid4().hex[:8]}",
            user_id="usr-operator-01",
            workspace_id="default-ops",
            target_system="postgresql",
            tool_name="create_operational_task",
            arguments=req_args,
            action_summary="Scale background worker pool",
            target_resource="worker-cluster"
        )
        appr_id = appr.id
        nonce = appr.nonce

    try:
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # 2. Query pending approvals
            list_resp = await client.get("/api/approvals?status_filter=pending", headers=OPERATOR_HEADERS)
            assert list_resp.status_code == 200
            pending_ids = [item["id"] for item in list_resp.json()]
            assert appr_id in pending_ids

            # 3. Approve and execute as Admin
            approve_resp = await client.post(f"/api/approvals/{appr_id}/approve", headers=ADMIN_HEADERS)
            assert approve_resp.status_code == 200
            res_data = approve_resp.json()
            assert res_data["status"] in ("SUCCESS", "FAILED")  # Execution ran and completed

            # 4. Verify status transitioned to succeeded or failed
            async with AsyncSessionLocal() as session:
                chk = (await session.execute(select(ApprovalRequest).where(ApprovalRequest.id == appr_id))).scalar_one()
                assert chk.approval_status in ("succeeded", "failed")
                assert chk.approved_by == "usr-admin-01"

                # 5. Verify single-use nonce is recorded in consumed_approval_tokens
                token_chk = (await session.execute(
                    select(ConsumedApprovalToken).where(ConsumedApprovalToken.nonce == nonce)
                )).scalar_one_or_none()
                assert token_chk is not None
                assert token_chk.approval_id == appr_id

            # 6. Double-approval attempt must be strictly rejected
            double_resp = await client.post(f"/api/approvals/{appr_id}/approve", headers=ADMIN_HEADERS)
            assert double_resp.status_code == 400
            assert "Cannot approve request in" in double_resp.json()["detail"]

    finally:
        async with AsyncSessionLocal() as session:
            await session.execute(delete(ConsumedApprovalToken).where(ConsumedApprovalToken.approval_id == appr_id))
            await session.execute(delete(ApprovalRequest).where(ApprovalRequest.id == appr_id))
            await session.commit()

@pytest.mark.asyncio
async def test_end_to_end_rejection_lifecycle():
    """Verify rejection transitions status, records reason, prevents execution, and blocks subsequent approval."""
    await init_system_db()
    transport = ASGITransport(app=app)
    
    async with AsyncSessionLocal() as session:
        appr = await approval_service.create_approval_request(
            db=session,
            execution_id=f"exec-p6-rej-{uuid.uuid4().hex[:8]}",
            user_id="usr-operator-01",
            workspace_id="default-ops",
            target_system="email",
            tool_name="send_email",
            arguments={"to": "external@vendor.com", "subject": "Notice", "body": "Hello"},
            action_summary="Send external email notification"
        )
        appr_id = appr.id

    try:
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # 1. Reject with reason
            reject_resp = await client.post(
                f"/api/approvals/{appr_id}/reject",
                json={"reason": "Security policy forbids unverified external domains"},
                headers=OPERATOR_HEADERS
            )
            assert reject_resp.status_code == 200
            rej_data = reject_resp.json()
            assert rej_data["status"] == "REJECTED"

            # 2. Check record in DB
            async with AsyncSessionLocal() as session:
                chk = (await session.execute(select(ApprovalRequest).where(ApprovalRequest.id == appr_id))).scalar_one()
                assert chk.approval_status == "rejected"
                assert "Security policy forbids" in chk.execution_result

            # 3. Subsequent approval attempt on rejected request must fail
            appr_again = await client.post(f"/api/approvals/{appr_id}/approve", headers=ADMIN_HEADERS)
            assert appr_again.status_code == 400
            assert "Cannot approve request in 'rejected' state" in appr_again.json()["detail"]

    finally:
        async with AsyncSessionLocal() as session:
            await session.execute(delete(ApprovalRequest).where(ApprovalRequest.id == appr_id))
            await session.commit()

@pytest.mark.asyncio
async def test_parameter_tampering_rejection():
    """Verify that if parameters are modified after proposal generation, approval fails with security error."""
    await init_system_db()
    transport = ASGITransport(app=app)

    async with AsyncSessionLocal() as session:
        appr = await approval_service.create_approval_request(
            db=session,
            execution_id=f"exec-p6-tamper-{uuid.uuid4().hex[:8]}",
            user_id="usr-operator-01",
            workspace_id="default-ops",
            target_system="postgresql",
            tool_name="update_incident_status",
            arguments={"incident_id": "INC-101", "status": "investigating"},
            action_summary="Set incident INC-101 to investigating"
        )
        appr_id = appr.id

        # Malicious tampering: Escalating to 'closed' directly in database without updating action_hash
        appr.canonical_action_arguments = json.dumps({"incident_id": "INC-101", "status": "closed"}, sort_keys=True)
        await session.commit()

    try:
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(f"/api/approvals/{appr_id}/approve", headers=ADMIN_HEADERS)
            assert resp.status_code == 400
            assert "tampering detected" in resp.json()["detail"].lower()

            async with AsyncSessionLocal() as session:
                chk = (await session.execute(select(ApprovalRequest).where(ApprovalRequest.id == appr_id))).scalar_one()
                assert chk.approval_status == "rejected"

    finally:
        async with AsyncSessionLocal() as session:
            await session.execute(delete(ApprovalRequest).where(ApprovalRequest.id == appr_id))
            await session.commit()

@pytest.mark.asyncio
async def test_expiration_15_minute_window_enforcement():
    """Verify requests past their 15-minute window are marked expired and blocked from execution."""
    await init_system_db()
    transport = ASGITransport(app=app)
    past_time = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=16)

    async with AsyncSessionLocal() as session:
        appr = await approval_service.create_approval_request(
            db=session,
            execution_id=f"exec-p6-exp-{uuid.uuid4().hex[:8]}",
            user_id="usr-operator-01",
            workspace_id="default-ops",
            target_system="postgresql",
            tool_name="create_operational_task",
            arguments={"title": "Stale task"},
            action_summary="Expired task proposal"
        )
        appr_id = appr.id
        appr.expires_at = past_time
        await session.commit()

    try:
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # 1. Listing approvals automatically prunes past-due pending requests to 'expired'
            list_resp = await client.get("/api/approvals", headers=OPERATOR_HEADERS)
            assert list_resp.status_code == 200
            item = next((x for x in list_resp.json() if x["id"] == appr_id), None)
            assert item is not None
            assert item["approval_status"] == "expired"

            # 2. Attempting to approve an expired request fails
            approve_resp = await client.post(f"/api/approvals/{appr_id}/approve", headers=ADMIN_HEADERS)
            assert approve_resp.status_code == 400
            assert "expired" in approve_resp.json()["detail"].lower()

    finally:
        async with AsyncSessionLocal() as session:
            await session.execute(delete(ApprovalRequest).where(ApprovalRequest.id == appr_id))
            await session.commit()

@pytest.mark.asyncio
async def test_nonce_replay_attack_prevention():
    """Verify that once a nonce is recorded in consumed_approval_tokens, execution using it is permanently blocked."""
    await init_system_db()
    test_nonce = f"nonce-replay-{uuid.uuid4().hex}"
    action_args = {"title": "Task A"}
    action_hash = compute_action_hash("create_operational_task", action_args)

    async with AsyncSessionLocal() as session:
        consumed = ConsumedApprovalToken(
            nonce=test_nonce,
            approval_id=f"appr-{uuid.uuid4().hex[:8]}",
            tool_name="create_operational_task",
            workspace_id="default-ops",
            action_hash=action_hash,
            consumed_at=datetime.datetime.now(datetime.timezone.utc)
        )
        session.add(consumed)
        
        # Create approval with the already consumed nonce
        appr = ApprovalRequest(
            id=f"appr-replay-{uuid.uuid4().hex[:8]}",
            execution_id=f"exec-replay-{uuid.uuid4().hex[:8]}",
            requesting_user_id="usr-operator-01",
            workspace_id="default-ops",
            target_system="postgresql",
            tool_name="create_operational_task",
            canonical_action_arguments=json.dumps(action_args, sort_keys=True),
            action_summary="Replay attack attempt",
            action_hash=action_hash,
            nonce=test_nonce,
            approval_status="pending",
            created_at=datetime.datetime.now(datetime.timezone.utc),
            expires_at=datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=15)
        )
        session.add(appr)
        await session.commit()
        appr_id = appr.id

    try:
        # Attempting approve_and_execute must be blocked by replay defense
        async with AsyncSessionLocal() as session:
            res = await approval_service.approve_and_execute(
                db=session,
                approval_id=appr_id,
                approver_user_id="usr-admin-01"
            )
            assert res["status"] == "SECURITY_ERROR"
            assert "replay attack detected" in res["error"].lower()

    finally:
        async with AsyncSessionLocal() as session:
            await session.execute(delete(ConsumedApprovalToken).where(ConsumedApprovalToken.nonce == test_nonce))
            await session.execute(delete(ApprovalRequest).where(ApprovalRequest.id == appr_id))
            await session.commit()

@pytest.mark.asyncio
async def test_cross_workspace_approval_isolation():
    """Verify members of Workspace A cannot view, approve, or reject requests from Workspace B."""
    await init_system_db()
    transport = ASGITransport(app=app)
    ws_b_id = f"ws-tenant-b-{uuid.uuid4().hex[:6]}"
    user_b_id = f"usr-tenant-b-{uuid.uuid4().hex[:6]}"

    async with AsyncSessionLocal() as session:
        ws_b = Workspace(id=ws_b_id, name="Tenant B", slug=f"tenant-b-{uuid.uuid4().hex[:6]}")
        user_b = User(
            id=user_b_id,
            email=f"admin-{uuid.uuid4().hex[:6]}@tenantb.internal",
            hashed_password="hash",
            full_name="Tenant B Admin",
            role="admin",
            is_active=True
        )
        session.add(ws_b)
        session.add(user_b)
        session.add(WorkspaceMember(workspace_id=ws_b_id, user_id=user_b_id, role="admin"))

        # Create approval belonging strictly to Tenant B
        appr = await approval_service.create_approval_request(
            db=session,
            execution_id=f"exec-b-{uuid.uuid4().hex[:8]}",
            user_id=user_b_id,
            workspace_id=ws_b_id,
            target_system="postgresql",
            tool_name="create_operational_task",
            arguments={"title": "Private Tenant B Task"},
            action_summary="Private Tenant B Action"
        )
        b_appr_id = appr.id

    try:
        # Default-ops admin (from Tenant A) tries to access Tenant B's approval
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            get_resp = await client.get(f"/api/approvals/{b_appr_id}", headers=ADMIN_HEADERS)
            assert get_resp.status_code == 404

            appr_resp = await client.post(f"/api/approvals/{b_appr_id}/approve", headers=ADMIN_HEADERS)
            assert appr_resp.status_code == 404

            rej_resp = await client.post(f"/api/approvals/{b_appr_id}/reject", headers=ADMIN_HEADERS)
            assert rej_resp.status_code == 404

    finally:
        async with AsyncSessionLocal() as session:
            await session.execute(delete(ApprovalRequest).where(ApprovalRequest.id == b_appr_id))
            await session.execute(delete(WorkspaceMember).where(WorkspaceMember.workspace_id == ws_b_id))
            await session.execute(delete(User).where(User.id == user_b_id))
            await session.execute(delete(Workspace).where(Workspace.id == ws_b_id))
            await session.commit()

@pytest.mark.asyncio
async def test_purge_inactive_approvals_endpoint():
    """Verify /api/approvals/purge deletes inactive, expired, and rejected items while preserving pending."""
    await init_system_db()
    transport = ASGITransport(app=app)
    
    created_ids = []
    async with AsyncSessionLocal() as session:
        # 1. Pending (should be preserved)
        p = await approval_service.create_approval_request(
            db=session,
            execution_id=f"exec-purge-p-{uuid.uuid4().hex[:6]}",
            user_id="usr-operator-01",
            workspace_id="default-ops",
            target_system="postgresql",
            tool_name="create_operational_task",
            arguments={"title": "Pending task"},
            action_summary="Keep me"
        )
        created_ids.append(p.id)

        # 2. Rejected (should be purged)
        r = await approval_service.create_approval_request(
            db=session,
            execution_id=f"exec-purge-r-{uuid.uuid4().hex[:6]}",
            user_id="usr-operator-01",
            workspace_id="default-ops",
            target_system="postgresql",
            tool_name="create_operational_task",
            arguments={"title": "Rejected task"},
            action_summary="Purge me"
        )
        r.approval_status = "rejected"
        created_ids.append(r.id)

        # 3. Expired (should be purged)
        e = await approval_service.create_approval_request(
            db=session,
            execution_id=f"exec-purge-e-{uuid.uuid4().hex[:6]}",
            user_id="usr-operator-01",
            workspace_id="default-ops",
            target_system="postgresql",
            tool_name="create_operational_task",
            arguments={"title": "Expired task"},
            action_summary="Purge me too"
        )
        e.approval_status = "expired"
        created_ids.append(e.id)
        await session.commit()

    try:
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            purge_resp = await client.post("/api/approvals/purge", headers=ADMIN_HEADERS)
            assert purge_resp.status_code == 200
            assert purge_resp.json()["status"] == "SUCCESS"
            assert purge_resp.json()["purged_count"] >= 2

            # Verify pending still exists
            async with AsyncSessionLocal() as session:
                pending_chk = (await session.execute(
                    select(ApprovalRequest).where(ApprovalRequest.id == created_ids[0])
                )).scalar_one_or_none()
                assert pending_chk is not None
                assert pending_chk.approval_status == "pending"

    finally:
        async with AsyncSessionLocal() as session:
            for cid in created_ids:
                await session.execute(delete(ApprovalRequest).where(ApprovalRequest.id == cid))
            await session.commit()
