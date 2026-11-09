"""
Test Suite: Enterprise Registration, Login, Company Accounts & Persistent Authentication
Verifies individual & company registration, email verification, password reset,
employee invitation, organization workspace isolation, and returning user login.
"""

import pytest
import asyncio
import uuid
import httpx
from sqlalchemy import select
from app.main import app
from app.core.db import get_db, AsyncSessionLocal
from app.models.models import User, Workspace, WorkspaceMember, WorkspaceInvitation

@pytest.fixture
def anyio_backend():
    return "asyncio"

@pytest.mark.asyncio
async def test_new_individual_registration_and_verification_flow():
    """Verifies complete registration, email verification, and authenticated login for an individual."""
    unique_email = f"operator-{uuid.uuid4().hex[:8]}@devops.internal"
    
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        # 1. Register new individual
        reg_payload = {
            "full_name": "DevOps Candidate",
            "email": unique_email,
            "password": "SecurePassword123!",
            "confirm_password": "SecurePassword123!"
        }
        reg_res = await client.post("/api/auth/register/individual", json=reg_payload)
        assert reg_res.status_code == 200, f"Registration failed: {reg_res.text}"
        data = reg_res.json()
        assert data["status"] == "SUCCESS"
        assert "verification_token" in data
        v_token = data["verification_token"]

        # 2. Attempt login prior to verification -> blocked with 403
        login_res = await client.post("/api/auth/login", json={
            "email": unique_email,
            "password": "SecurePassword123!"
        })
        assert login_res.status_code == 403
        assert "not been verified" in login_res.json()["detail"]

        # 3. Verify email with verification token
        verify_res = await client.post("/api/auth/verify-email", json={"token": v_token})
        assert verify_res.status_code == 200
        assert verify_res.json()["status"] == "SUCCESS"

        # 4. Login after verification -> succeeds with 200 and access token
        login_success = await client.post("/api/auth/login", json={
            "email": unique_email,
            "password": "SecurePassword123!"
        })
        assert login_success.status_code == 200
        auth_data = login_success.json()
        assert "access_token" in auth_data
        assert auth_data["user"]["email"] == unique_email.lower()
        assert auth_data["user"]["role"] == "operator"
        assert auth_data["user"]["account_type"] == "individual"

@pytest.mark.asyncio
async def test_duplicate_email_and_password_mismatch_validation():
    """Verifies that duplicate registrations and mismatched passwords are strictly rejected."""
    existing_email = f"dup-{uuid.uuid4().hex[:8]}@example.com"
    
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        # Register first
        await client.post("/api/auth/register/individual", json={
            "full_name": "First User",
            "email": existing_email,
            "password": "Password123!",
            "confirm_password": "Password123!"
        })

        # Duplicate email attempt
        dup_res = await client.post("/api/auth/register/individual", json={
            "full_name": "Second User",
            "email": existing_email,
            "password": "Password123!",
            "confirm_password": "Password123!"
        })
        assert dup_res.status_code == 400
        assert "already exists" in dup_res.json()["detail"]

        # Mismatched password attempt
        mismatch_res = await client.post("/api/auth/register/individual", json={
            "full_name": "Mismatch User",
            "email": f"diff-{uuid.uuid4().hex[:8]}@example.com",
            "password": "Password123!",
            "confirm_password": "DifferentPassword123!"
        })
        assert mismatch_res.status_code == 400
        assert "Passwords do not match" in mismatch_res.json()["detail"]

@pytest.mark.asyncio
async def test_new_company_registration_and_workspace_isolation():
    """Verifies company registration, isolated workspace provisioning, and admin privilege assignment."""
    admin_email = f"cto-{uuid.uuid4().hex[:8]}@acmecorp.com"
    company_name = f"Acme Corporation {uuid.uuid4().hex[:4]}"
    
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        # 1. Register company
        company_payload = {
            "company_name": company_name,
            "company_email": f"ops@{uuid.uuid4().hex[:6]}.com",
            "admin_full_name": "Acme CTO",
            "admin_email": admin_email,
            "password": "CompanySecret123!",
            "confirm_password": "CompanySecret123!"
        }
        res = await client.post("/api/auth/register/company", json=company_payload)
        assert res.status_code == 200
        data = res.json()
        assert "workspace_id" in data
        assert "verification_token" in data
        ws_id = data["workspace_id"]
        v_token = data["verification_token"]

        # 2. Verify admin email
        await client.post("/api/auth/verify-email", json={"token": v_token})

        # 3. Authenticate company admin
        login_res = await client.post("/api/auth/login", json={
            "email": admin_email,
            "password": "CompanySecret123!"
        })
        assert login_res.status_code == 200
        user_info = login_res.json()["user"]
        assert user_info["role"] == "admin"
        assert user_info["account_type"] == "company"
        assert user_info["company_name"] == company_name
        assert user_info["workspace_id"] == ws_id

@pytest.mark.asyncio
async def test_password_recovery_and_reset_lifecycle():
    """Verifies the complete forgot password and reset password lifecycle."""
    user_email = f"reset-{uuid.uuid4().hex[:8]}@enterprise.internal"
    
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        # Register and verify
        reg_res = await client.post("/api/auth/register/individual", json={
            "full_name": "Reset Candidate",
            "email": user_email,
            "password": "OldPassword123!",
            "confirm_password": "OldPassword123!"
        })
        v_token = reg_res.json()["verification_token"]
        await client.post("/api/auth/verify-email", json={"token": v_token})

        # Request password reset
        forgot_res = await client.post("/api/auth/forgot-password", json={"email": user_email})
        assert forgot_res.status_code == 200

        # Retrieve reset token from DB
        async with AsyncSessionLocal() as session:
            stmt = select(User).where(User.email == user_email.lower())
            user = (await session.execute(stmt)).scalar_one()
            assert user.reset_password_token is not None
            r_token = user.reset_password_token

        # Reset password with token
        reset_res = await client.post("/api/auth/reset-password", json={
            "token": r_token,
            "new_password": "BrandNewPassword456!",
            "confirm_password": "BrandNewPassword456!"
        })
        assert reset_res.status_code == 200

        # Login with old password fails
        old_login = await client.post("/api/auth/login", json={
            "email": user_email,
            "password": "OldPassword123!"
        })
        assert old_login.status_code == 401

        # Login with new password succeeds
        new_login = await client.post("/api/auth/login", json={
            "email": user_email,
            "password": "BrandNewPassword456!"
        })
        assert new_login.status_code == 200

@pytest.mark.asyncio
async def test_company_employee_invitation_and_workspace_enrollment():
    """Verifies company employee invitation dispatch and workspace enrollment."""
    admin_email = f"admin-{uuid.uuid4().hex[:8]}@delta.internal"
    employee_email = f"emp-{uuid.uuid4().hex[:8]}@delta.internal"
    
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        # 1. Register company and admin
        comp_res = await client.post("/api/auth/register/company", json={
            "company_name": "Delta Enterprise",
            "admin_full_name": "Delta Admin",
            "admin_email": admin_email,
            "password": "DeltaPassword123!",
            "confirm_password": "DeltaPassword123!"
        })
        v_token = comp_res.json()["verification_token"]
        ws_id = comp_res.json()["workspace_id"]
        await client.post("/api/auth/verify-email", json={"token": v_token})

        # 2. Login admin and get access token
        login_res = await client.post("/api/auth/login", json={
            "email": admin_email,
            "password": "DeltaPassword123!"
        })
        admin_token = login_res.json()["access_token"]

        # 3. Admin invites employee
        invite_res = await client.post(
            "/api/auth/invite",
            json={"email": employee_email, "role": "operator"},
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert invite_res.status_code == 200
        invite_token = invite_res.json()["invitation_token"]

        # 4. Employee registers using invite token
        reg_invite_res = await client.post("/api/auth/register-invite", json={
            "token": invite_token,
            "full_name": "Delta Engineer",
            "password": "EngineerSecret123!",
            "confirm_password": "EngineerSecret123!"
        })
        assert reg_invite_res.status_code == 200

        # 5. Employee logs in -> belongs to Delta company workspace
        emp_login = await client.post("/api/auth/login", json={
            "email": employee_email,
            "password": "EngineerSecret123!"
        })
        assert emp_login.status_code == 200
        emp_user = emp_login.json()["user"]
        assert emp_user["role"] == "operator"
        assert emp_user["workspace_id"] == ws_id

@pytest.mark.asyncio
async def test_existing_seed_admin_login_remains_operational():
    """Guarantees backward compatibility for existing enterprise administrator credentials."""
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        res = await client.post("/api/auth/login", json={
            "email": "admin@opspilot.internal",
            "password": "admin123"
        })
        assert res.status_code == 200
        data = res.json()
        assert data["user"]["role"] == "admin"
        assert len(data["user"]["permissions"]) == 21

@pytest.mark.asyncio
async def test_invalid_passwords_and_unregistered_user_rejection():
    """Verifies that short passwords and unregistered users are cleanly rejected with generic errors."""
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        # Short password (< 8 chars)
        short_pw_res = await client.post("/api/auth/register/individual", json={
            "full_name": "Short Pw User",
            "email": f"short-{uuid.uuid4().hex[:6]}@example.com",
            "password": "123",
            "confirm_password": "123"
        })
        assert short_pw_res.status_code == 400
        assert "at least 8 characters" in short_pw_res.json()["detail"]

        # Unregistered user login attempt
        unreg_res = await client.post("/api/auth/login", json={
            "email": f"ghost-{uuid.uuid4().hex[:8]}@nowhere.com",
            "password": "AnyPassword123!"
        })
        assert unreg_res.status_code == 401
        assert "Incorrect email or password" in unreg_res.json()["detail"]

@pytest.mark.asyncio
async def test_returning_user_authentication_and_dashboard_loading():
    """Verifies that a registered user can sign out, return later, sign in, and load the dashboard."""
    user_email = f"returning-{uuid.uuid4().hex[:8]}@persistent.org"
    company_name = f"Persistent Systems {uuid.uuid4().hex[:4]}"

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        # 1. Register Company with optional metadata
        reg_res = await client.post("/api/auth/register/company", json={
            "company_name": company_name,
            "company_email": f"contact@{uuid.uuid4().hex[:6]}.com",
            "company_website": "https://persistentsystems.internal",
            "industry": "Technology & SaaS",
            "admin_full_name": "Persistent Admin",
            "admin_email": user_email,
            "password": "PersistentPassword123!",
            "confirm_password": "PersistentPassword123!"
        })
        assert reg_res.status_code == 200
        v_token = reg_res.json()["verification_token"]
        ws_id = reg_res.json()["workspace_id"]

        # 2. Verify Email
        await client.post("/api/auth/verify-email", json={"token": v_token})

        # 3. First Login Session
        login_1 = await client.post("/api/auth/login", json={
            "email": user_email,
            "password": "PersistentPassword123!"
        })
        assert login_1.status_code == 200
        token_1 = login_1.json()["access_token"]

        # 4. Access Dashboard with Token
        dash_res = await client.get("/api/dashboard/stats", headers={"Authorization": f"Bearer {token_1}"})
        assert dash_res.status_code == 200
        dash_data = dash_res.json()
        assert "user" in dash_data
        assert dash_data["user"]["name"] == "Persistent Admin"

        # 5. Simulate Returning User (Later session re-login with same credentials)
        login_2 = await client.post("/api/auth/login", json={
            "email": user_email,
            "password": "PersistentPassword123!"
        })
        assert login_2.status_code == 200
        token_2 = login_2.json()["access_token"]
        assert token_2 is not None

        # Verify DB persistence directly via new session
        async with AsyncSessionLocal() as session:
            stmt = select(Workspace).where(Workspace.id == ws_id)
            ws_record = (await session.execute(stmt)).scalar_one()
            assert ws_record.name == company_name
            assert ws_record.website == "https://persistentsystems.internal"
            assert ws_record.industry == "Technology & SaaS"


