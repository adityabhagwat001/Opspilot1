"""
Test Suite: Phase 3 - Strict Multi-Tenant Organization Data Isolation
Verifies that all enterprise resources are strictly segregated by organization workspace:
1. Repository Monitoring Isolation & Shared-Name Independence.
2. CI/CD Failures and Activity Stream Isolation.
3. AI Fix Proposals and Execution Boundary Isolation.
4. Approval Center Requests & Tampering Prevention across tenants.
5. Cross-Tenant X-Workspace-Id Header Spoofing Prevention (403 Forbidden).
6. Enterprise Audit Log Tenant Isolation.
7. Dashboard Telemetry & Operations Summary Isolation.
8. AI Assistant / Chat Conversation Tenant Isolation.
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
    MonitoredRepository, 
    WorkflowFailure, 
    FixProposal, 
    ApprovalRequest, 
    AuditLog,
    GitHubEvent,
    AgentConversation,
    utc_now
)

@pytest.fixture
def anyio_backend():
    return "asyncio"


async def setup_company(client: httpx.AsyncClient, name_prefix: str):
    """Registers and verifies a fresh test company and administrator."""
    company_name = f"{name_prefix} Technologies {uuid.uuid4().hex[:6]}"
    admin_email = f"admin-{uuid.uuid4().hex[:6]}@{name_prefix.lower()}.internal"
    password = "TenantPassword123!"

    reg_res = await client.post("/api/auth/register/company", json={
        "company_name": company_name,
        "company_email": f"ops@{name_prefix.lower()}.internal",
        "company_website": f"https://{name_prefix.lower()}.internal",
        "industry": "Enterprise SaaS",
        "admin_full_name": f"{name_prefix} Admin",
        "admin_email": admin_email,
        "password": password,
        "confirm_password": password
    })
    assert reg_res.status_code == 200, f"Setup failed: {reg_res.text}"
    data = reg_res.json()
    ws_id = data["workspace_id"]
    v_token = data["verification_token"]

    # Verify email
    ver_res = await client.post("/api/auth/verify-email", json={"token": v_token})
    assert ver_res.status_code == 200

    # Sign in
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
async def test_repository_monitoring_tenant_isolation_and_shared_names():
    """
    Verifies that Company Alpha and Company Beta have fully isolated repository rosters,
    and can both independently monitor the exact same repository name without conflicts.
    """
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        alpha = await setup_company(client, "AlphaRepo")
        beta = await setup_company(client, "BetaRepo")

        shared_repo = "org-common/public-service"

        # 1. Alpha monitors shared_repo and an alpha-specific repo
        r1 = await client.post("/api/github/repositories/monitor", headers=alpha["headers"], json={
            "repo_full_name": shared_repo,
            "is_monitored": True
        })
        assert r1.status_code == 200

        r2 = await client.post("/api/github/repositories/monitor", headers=alpha["headers"], json={
            "repo_full_name": "alpha-corp/backend-api",
            "is_monitored": True
        })
        assert r2.status_code == 200

        # 2. Beta also monitors shared_repo and a beta-specific repo -> must succeed without UNIQUE collision
        r3 = await client.post("/api/github/repositories/monitor", headers=beta["headers"], json={
            "repo_full_name": shared_repo,
            "is_monitored": True
        })
        assert r3.status_code == 200

        r4 = await client.post("/api/github/repositories/monitor", headers=beta["headers"], json={
            "repo_full_name": "beta-corp/payments-service",
            "is_monitored": True
        })
        assert r4.status_code == 200

        # 3. Verify in database that repositories are partitioned by workspace_id
        async with AsyncSessionLocal() as session:
            alpha_repos = (await session.execute(
                select(MonitoredRepository).where(MonitoredRepository.workspace_id == alpha["workspace_id"])
            )).scalars().all()
            beta_repos = (await session.execute(
                select(MonitoredRepository).where(MonitoredRepository.workspace_id == beta["workspace_id"])
            )).scalars().all()

            alpha_names = {r.full_name for r in alpha_repos}
            beta_names = {r.full_name for r in beta_repos}

            assert shared_repo in alpha_names
            assert "alpha-corp/backend-api" in alpha_names
            assert "beta-corp/payments-service" not in alpha_names

            assert shared_repo in beta_names
            assert "beta-corp/payments-service" in beta_names
            assert "alpha-corp/backend-api" not in beta_names


@pytest.mark.asyncio
async def test_cicd_failures_and_activity_tenant_isolation():
    """
    Verifies that CI/CD failures and event streams created in Company Alpha
    are completely invisible to Company Beta.
    """
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        alpha = await setup_company(client, "AlphaFail")
        beta = await setup_company(client, "BetaFail")

        # Create monitored repository for Alpha
        repo_name = "alpha-corp/microservice"
        await client.post("/api/github/repositories/monitor", headers=alpha["headers"], json={
            "repo_full_name": repo_name,
            "is_monitored": True
        })

        # Inject failure and event for Alpha directly into DB
        fail_id = f"fail-{uuid.uuid4().hex[:12]}"
        event_id = f"evt-{uuid.uuid4().hex[:12]}"

        async with AsyncSessionLocal() as session:
            failure = WorkflowFailure(
                id=fail_id,
                workspace_id=alpha["workspace_id"],
                repo_full_name=repo_name,
                run_id=987654321,
                workflow_name="Deploy Production",
                event="push",
                head_branch="main",
                commit_sha="a1b2c3d4e5f6",
                actor="alpha-dev",
                failing_step="Kubernetes Deployment",
                error_log_snippet="OOMKilled on container pod",
                status="detected"
            )
            event = GitHubEvent(
                id=event_id,
                workspace_id=alpha["workspace_id"],
                repo_full_name=repo_name,
                event_type="workflow_run",
                action="completed",
                actor="alpha-dev",
                summary="Deploy Production failed on main"
            )
            session.add_all([failure, event])
            await session.commit()

        # 1. Alpha queries failures -> sees the failure
        alpha_failures = (await client.get("/api/github/failures", headers=alpha["headers"])).json()
        assert any(f["id"] == fail_id for f in alpha_failures)

        # 2. Beta queries failures -> 0 failures visible
        beta_failures = (await client.get("/api/github/failures", headers=beta["headers"])).json()
        assert not any(f["id"] == fail_id for f in beta_failures)

        # 3. Alpha queries activity -> sees the event
        alpha_activity = (await client.get("/api/github/activity", headers=alpha["headers"])).json()
        assert any(a["id"] == event_id for a in alpha_activity)

        # 4. Beta queries activity -> 0 activity records visible
        beta_activity = (await client.get("/api/github/activity", headers=beta["headers"])).json()
        assert not any(a["id"] == event_id for a in beta_activity)


@pytest.mark.asyncio
async def test_ai_proposals_and_execution_tenant_isolation():
    """
    Verifies that AI Fix Proposals for Company Alpha cannot be viewed or executed by Company Beta.
    """
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        alpha = await setup_company(client, "AlphaProp")
        beta = await setup_company(client, "BetaProp")

        # Monitor repo in Alpha
        repo_name = "alpha-corp/auth-service"
        await client.post("/api/github/repositories/monitor", headers=alpha["headers"], json={
            "repo_full_name": repo_name,
            "is_monitored": True
        })

        prop_id = f"prop-{uuid.uuid4().hex[:12]}"
        async with AsyncSessionLocal() as session:
            proposal = FixProposal(
                id=prop_id,
                workspace_id=alpha["workspace_id"],
                repo_full_name=repo_name,
                fix_branch="fix/memory-leak",
                title="Fix Memory Leak in Auth Cache",
                explanation="Evict expired cache keys periodically",
                status="proposed"
            )
            session.add(proposal)
            await session.commit()

        # 1. Alpha lists proposals -> sees proposal
        alpha_props = (await client.get("/api/github/proposals", headers=alpha["headers"])).json()
        assert any(p["id"] == prop_id for p in alpha_props)

        # 2. Beta lists proposals -> does NOT see proposal
        beta_props = (await client.get("/api/github/proposals", headers=beta["headers"])).json()
        assert not any(p["id"] == prop_id for p in beta_props)

        # 3. Beta attempts to execute Alpha's proposal -> 404 Not Found
        exec_attempt = await client.post(f"/api/github/proposals/{prop_id}/execute", headers=beta["headers"])
        assert exec_attempt.status_code == 404

        # 4. Beta attempts to delete Alpha's proposal -> 404 Not Found
        del_attempt = await client.delete(f"/api/github/proposals/{prop_id}", headers=beta["headers"])
        assert del_attempt.status_code == 404


@pytest.mark.asyncio
async def test_approval_requests_tenant_isolation():
    """
    Verifies that human approval requests created in Company Alpha
    cannot be seen, approved, rejected, or purged by Company Beta.
    """
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        alpha = await setup_company(client, "AlphaAppr")
        beta = await setup_company(client, "BetaAppr")

        # Create an approval request for Alpha
        appr_id = f"appr-{uuid.uuid4().hex[:12]}"
        exec_id = f"exec-{uuid.uuid4().hex[:12]}"
        now = datetime.datetime.now(datetime.timezone.utc)

        async with AsyncSessionLocal() as session:
            # Create conversation and execution first
            conv = AgentConversation(
                id=f"conv-{uuid.uuid4().hex[:8]}",
                user_id=alpha["admin_id"],
                workspace_id=alpha["workspace_id"],
                title="Deployment Request"
            )
            session.add(conv)
            appr = ApprovalRequest(
                id=appr_id,
                execution_id=exec_id,
                requesting_user_id=alpha["admin_id"],
                workspace_id=alpha["workspace_id"],
                target_system="github",
                tool_name="merge_pull_request",
                canonical_action_arguments='{"repo": "alpha-corp/app", "pull_number": 42}',
                action_summary="Merge PR #42 into main",
                action_hash="hash-12345",
                approval_status="pending",
                expires_at=now + datetime.timedelta(minutes=30)
            )
            session.add(appr)
            await session.commit()

        # 1. Alpha lists approvals -> sees request
        alpha_apprs = (await client.get("/api/approvals", headers=alpha["headers"])).json()
        assert any(a["id"] == appr_id for a in alpha_apprs)

        # 2. Beta lists approvals -> 0 approvals
        beta_apprs = (await client.get("/api/approvals", headers=beta["headers"])).json()
        assert not any(a["id"] == appr_id for a in beta_apprs)

        # 3. Beta tries to fetch Alpha's approval by ID -> 404
        get_res = await client.get(f"/api/approvals/{appr_id}", headers=beta["headers"])
        assert get_res.status_code == 404

        # 4. Beta tries to approve Alpha's request -> 404
        approve_res = await client.post(f"/api/approvals/{appr_id}/approve", headers=beta["headers"])
        assert approve_res.status_code == 404

        # 5. Beta tries to reject Alpha's request -> 404
        reject_res = await client.post(f"/api/approvals/{appr_id}/reject", headers=beta["headers"])
        assert reject_res.status_code == 404


@pytest.mark.asyncio
async def test_cross_tenant_workspace_header_spoofing_prevention():
    """
    Verifies that Company Beta's administrator CANNOT access Company Alpha's workspace
    simply by passing Alpha's workspace_id in the 'X-Workspace-Id' request header.
    Must return 403 Forbidden.
    """
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        alpha = await setup_company(client, "AlphaSpoof")
        beta = await setup_company(client, "BetaSpoof")

        # Beta's admin crafts a request containing Alpha's workspace ID in X-Workspace-Id
        spoofed_headers = {
            "Authorization": f"Bearer {beta['token']}",
            "X-Workspace-Id": alpha["workspace_id"]
        }

        # Attempt to access Company Details of Alpha -> 403 Forbidden
        comp_res = await client.get("/api/company", headers=spoofed_headers)
        assert comp_res.status_code == 403
        assert "not a member" in comp_res.json()["detail"].lower()

        # Attempt to access Approvals of Alpha -> 403 Forbidden
        appr_res = await client.get("/api/approvals", headers=spoofed_headers)
        assert appr_res.status_code == 403

        # Attempt to access Audit logs of Alpha -> 403 Forbidden
        audit_res = await client.get("/api/audit", headers=spoofed_headers)
        assert audit_res.status_code == 403


@pytest.mark.asyncio
async def test_audit_logs_and_dashboard_tenant_isolation():
    """
    Verifies that audit log entries and dashboard metrics remain strictly isolated by organization.
    """
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        alpha = await setup_company(client, "AlphaAudit")
        beta = await setup_company(client, "BetaAudit")

        audit_id = f"aud-{uuid.uuid4().hex[:12]}"
        async with AsyncSessionLocal() as session:
            audit = AuditLog(
                id=audit_id,
                user_id=alpha["admin_id"],
                workspace_id=alpha["workspace_id"],
                action_type="WRITE_EXECUTED",
                target_system="github",
                tool_name="create_issue",
                result_summary="Created critical issue #99",
                status="success"
            )
            session.add(audit)
            await session.commit()

        # Alpha queries audit -> sees entry
        alpha_logs = (await client.get("/api/audit", headers=alpha["headers"])).json()
        assert any(l["id"] == audit_id for l in alpha_logs)

        # Beta queries audit -> does NOT see entry
        beta_logs = (await client.get("/api/audit", headers=beta["headers"])).json()
        assert not any(l["id"] == audit_id for l in beta_logs)

        # Dashboard stats for Beta
        beta_stats = (await client.get("/api/dashboard/stats", headers=beta["headers"])).json()
        assert beta_stats["workspace_id"] == beta["workspace_id"]
        assert not any(l["summary"] == "Created critical issue #99" for l in beta_stats.get("recent_activity", []))


@pytest.mark.asyncio
async def test_chat_conversations_tenant_isolation():
    """
    Verifies that AI chat conversations created within one workspace
    are strictly segregated and cannot be read or written from another workspace.
    """
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        alpha = await setup_company(client, "AlphaChat")
        beta = await setup_company(client, "BetaChat")

        # 1. Alpha creates conversation
        conv_res = await client.post("/api/chat/conversations", headers=alpha["headers"], json={"title": "Alpha Operations"})
        assert conv_res.status_code == 200
        conv_id = conv_res.json()["id"]

        # 2. Alpha lists conversations -> sees conversation
        alpha_convs = (await client.get("/api/chat/conversations", headers=alpha["headers"])).json()
        assert any(c["id"] == conv_id for c in alpha_convs)

        # 3. Beta lists conversations -> 0 conversations
        beta_convs = (await client.get("/api/chat/conversations", headers=beta["headers"])).json()
        assert not any(c["id"] == conv_id for c in beta_convs)

        # 4. Beta attempts to read messages of Alpha's conversation -> 404
        msg_attempt = await client.get(f"/api/chat/conversations/{conv_id}/messages", headers=beta["headers"])
        assert msg_attempt.status_code == 404

