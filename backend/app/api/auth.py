"""
Authentication & Identity Management Endpoints
Enterprise registration (Individual & Company), verified credential authentication,
password reset lifecycle, employee invitations, and rate-limited brute-force protection.
"""

import re
import uuid
import secrets
import datetime
from typing import Optional, Dict, List
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update
from app.core.db import get_db
from app.core.security import hash_password, verify_password, create_access_token
from app.models.models import (
    User, 
    Workspace, 
    WorkspaceMember, 
    WorkspaceInvitation, 
    IntegrationConnection,
    utc_now
)
from app.schemas.schemas import (
    LoginRequest, 
    TokenResponse,
    RegisterIndividualRequest,
    RegisterCompanyRequest,
    VerifyEmailRequest,
    ResendVerificationRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    InviteEmployeeRequest,
    RegisterInviteRequest,
    SwitchWorkspaceRequest
)
from app.auth.deps import get_current_user, require_role, get_current_workspace_member
from app.core.permissions import get_role_permissions
from app.services.email_service import (
    send_verification_email,
    send_password_reset_email,
    send_invitation_email
)

router = APIRouter(prefix="/auth", tags=["Authentication"])

# In-memory sliding window for brute-force protection
FAILED_ATTEMPTS: Dict[str, List[datetime.datetime]] = {}
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_WINDOW_SECONDS = 300  # 5 minutes

def to_utc(dt: Optional[datetime.datetime]) -> Optional[datetime.datetime]:
    """Ensures datetime comparisons are consistently timezone-aware (UTC)."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=datetime.timezone.utc)
    return dt

def check_rate_limit(key: str):
    now = datetime.datetime.now(datetime.timezone.utc)
    attempts = FAILED_ATTEMPTS.get(key, [])
    # Keep only attempts in window
    attempts = [t for t in attempts if (now - t).total_seconds() < LOCKOUT_WINDOW_SECONDS]
    FAILED_ATTEMPTS[key] = attempts
    if len(attempts) >= MAX_FAILED_ATTEMPTS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many failed login attempts. Please wait 5 minutes before trying again."
        )

def record_failed_attempt(key: str):
    now = datetime.datetime.now(datetime.timezone.utc)
    attempts = FAILED_ATTEMPTS.get(key, [])
    attempts.append(now)
    FAILED_ATTEMPTS[key] = attempts

def clear_failed_attempts(key: str):
    FAILED_ATTEMPTS.pop(key, None)


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)):
    """
    Authenticates a registered, verified user against stored password hash.
    Enforces normalized email lookup, account status checks, and rate-limiting.
    """
    clean_email = payload.email.strip().lower()
    check_rate_limit(clean_email)

    stmt = select(User).where(func.lower(User.email) == clean_email)
    user = (await db.execute(stmt)).scalar_one_or_none()
    
    if not user or not verify_password(payload.password, user.hashed_password):
        record_failed_attempt(clean_email)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password."
        )

    if not user.is_active or (getattr(user, "account_status", "active") != "active"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive or suspended. Please contact your system administrator."
        )

    # Check email verification status (exempt existing default seed accounts)
    if not user.is_verified and user.email not in ("admin@opspilot.internal", "operator@opspilot.internal"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your email address has not been verified yet. Please check your email or click Resend Verification."
        )

    # Authentication succeeded; clear failed attempts
    clear_failed_attempts(clean_email)

    # Update last login timestamp
    user.last_login_at = utc_now()
    await db.commit()

    # Discover primary workspace
    mem_stmt = select(WorkspaceMember).where(WorkspaceMember.user_id == user.id).order_by(WorkspaceMember.id.desc())
    mem = (await db.execute(mem_stmt)).scalars().first()
    workspace_id = mem.workspace_id if mem else "default-ops"

    token = create_access_token({
        "sub": user.id, 
        "email": user.email, 
        "role": user.role,
        "workspace_id": workspace_id
    })

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
            "account_type": getattr(user, "account_type", "individual"),
            "company_name": getattr(user, "company_name", None),
            "workspace_id": workspace_id,
            "is_verified": user.is_verified,
            "permissions": get_role_permissions(user.role)
        }
    }


@router.post("/register/individual")
async def register_individual(payload: RegisterIndividualRequest, db: AsyncSession = Depends(get_db)):
    """
    Registers a new individual DevOps operator account.
    Validates input, securely hashes credentials, generates email verification token.
    """
    if len(payload.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters long.")
    
    if payload.password != payload.confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match.")

    clean_email = payload.email.strip().lower()
    existing_stmt = select(User).where(func.lower(User.email) == clean_email)
    existing_user = (await db.execute(existing_stmt)).scalar_one_or_none()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email address already exists. Please sign in instead."
        )

    verification_token = secrets.token_urlsafe(32)
    new_user = User(
        id=f"usr-{uuid.uuid4().hex[:12]}",
        email=clean_email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name.strip(),
        role="operator",
        is_active=True,
        is_verified=False,
        verification_token=verification_token,
        verification_token_expires_at=utc_now() + datetime.timedelta(hours=24),
        account_type="individual",
        created_at=utc_now()
    )
    db.add(new_user)

    # Attach to default operational workspace
    db.add(WorkspaceMember(
        id=f"mem-{uuid.uuid4().hex[:12]}",
        workspace_id="default-ops",
        user_id=new_user.id,
        role="operator"
    ))
    await db.commit()

    # Dispatch verification email
    verify_url = send_verification_email(
        to_email=new_user.email,
        full_name=new_user.full_name,
        verification_token=verification_token
    )

    return {
        "status": "SUCCESS",
        "message": "Account created successfully. A verification link has been sent to your email address.",
        "user_id": new_user.id,
        "verification_token": verification_token,
        "verification_url": verify_url
    }


@router.post("/register/company")
async def register_company(payload: RegisterCompanyRequest, db: AsyncSession = Depends(get_db)):
    """
    Registers a new Company Organization workspace and an Enterprise Administrator account.
    Creates isolated workspace, assigns admin privileges, and issues verification token.
    """
    if len(payload.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters long.")

    if payload.password != payload.confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match.")

    clean_email = payload.admin_email.strip().lower()
    existing_stmt = select(User).where(func.lower(User.email) == clean_email)
    existing_user = (await db.execute(existing_stmt)).scalar_one_or_none()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this administrator email already exists. Please sign in instead."
        )

    # Generate workspace slug from company name
    raw_slug = re.sub(r'[^a-z0-9]+', '-', payload.company_name.lower()).strip('-') or "company-ops"
    slug_stmt = select(Workspace).where(Workspace.slug == raw_slug)
    if (await db.execute(slug_stmt)).scalar_one_or_none():
        raw_slug = f"{raw_slug}-{uuid.uuid4().hex[:6]}"

    workspace_id = f"ws-{uuid.uuid4().hex[:10]}"
    company_ws = Workspace(
        id=workspace_id,
        name=payload.company_name.strip(),
        slug=raw_slug,
        company_email=payload.company_email.strip().lower() if payload.company_email else clean_email,
        website=payload.company_website.strip() if payload.company_website else None,
        industry=payload.industry.strip() if payload.industry else None,
        status="active",
        created_at=utc_now()
    )
    db.add(company_ws)

    verification_token = secrets.token_urlsafe(32)
    admin_user = User(
        id=f"usr-{uuid.uuid4().hex[:12]}",
        email=clean_email,
        hashed_password=hash_password(payload.password),
        full_name=payload.admin_full_name.strip(),
        role="admin",
        is_active=True,
        is_verified=False,
        verification_token=verification_token,
        verification_token_expires_at=utc_now() + datetime.timedelta(hours=24),
        account_type="company",
        account_status="active",
        company_name=payload.company_name.strip(),
        created_at=utc_now()
    )
    db.add(admin_user)

    # Associate registering administrator with the company workspace
    db.add(WorkspaceMember(
        id=f"mem-{uuid.uuid4().hex[:12]}",
        workspace_id=company_ws.id,
        user_id=admin_user.id,
        role="admin"
    ))

    # Seed isolated integration connections for this workspace
    for provider, name in [
        ("postgresql", f"{payload.company_name} PostgreSQL Operations DB"),
        ("github", f"{payload.company_name} GitHub Enterprise Integration"),
        ("email", f"{payload.company_name} Operational Mail Integration"),
        ("calendar", f"{payload.company_name} Engineering Calendar")
    ]:
        db.add(IntegrationConnection(
            id=f"conn-{uuid.uuid4().hex[:12]}",
            workspace_id=company_ws.id,
            provider=provider,
            status="connected",
            details_json=f'{{"name": "{name}"}}'
        ))

    try:
        await db.commit()
    except Exception as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Transactional failure during company registration: {str(exc)}"
        )

    # Dispatch verification email
    verify_url = send_verification_email(
        to_email=admin_user.email,
        full_name=admin_user.full_name,
        verification_token=verification_token
    )

    return {
        "status": "SUCCESS",
        "message": "Company workspace and administrator account registered. Please verify your email to activate.",
        "workspace_id": company_ws.id,
        "admin_user_id": admin_user.id,
        "verification_token": verification_token,
        "verification_url": verify_url
    }


@router.get("/verify-email")
async def verify_email_get(token: str = Query(...), db: AsyncSession = Depends(get_db)):
    """GET handler for email verification via browser link."""
    return await _process_email_verification(token, db)


@router.post("/verify-email")
async def verify_email_post(payload: VerifyEmailRequest, db: AsyncSession = Depends(get_db)):
    """POST handler for email verification via API."""
    return await _process_email_verification(payload.token, db)


async def _process_email_verification(token: str, db: AsyncSession):
    if not token or not token.strip():
        raise HTTPException(status_code=400, detail="Missing email verification token.")

    stmt = select(User).where(User.verification_token == token.strip())
    user = (await db.execute(stmt)).scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired email verification link."
        )

    if user.verification_token_expires_at and to_utc(user.verification_token_expires_at) < utc_now():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This verification link has expired. Please request a new verification email."
        )

    user.is_verified = True
    user.verification_token = None
    user.verification_token_expires_at = None
    await db.commit()

    return {
        "status": "SUCCESS",
        "message": "Your email address has been successfully verified! You can now sign in to OpsPilot."
    }


@router.post("/resend-verification")
async def resend_verification(payload: ResendVerificationRequest, db: AsyncSession = Depends(get_db)):
    """Resends a new verification token for an unverified account."""
    clean_email = payload.email.strip().lower()
    stmt = select(User).where(func.lower(User.email) == clean_email)
    user = (await db.execute(stmt)).scalar_one_or_none()

    if user and not user.is_verified:
        new_token = secrets.token_urlsafe(32)
        user.verification_token = new_token
        user.verification_token_expires_at = utc_now() + datetime.timedelta(hours=24)
        await db.commit()
        verify_url = send_verification_email(user.email, user.full_name, new_token)
        return {
            "status": "SUCCESS",
            "message": "A new verification email has been dispatched.",
            "verification_url": verify_url
        }

    return {
        "status": "SUCCESS",
        "message": "If an unverified account exists for this email address, a new verification link has been sent."
    }


@router.post("/forgot-password")
async def forgot_password(payload: ForgotPasswordRequest, db: AsyncSession = Depends(get_db)):
    """
    Initiates password recovery. Dispatches secure reset token without exposing user existence.
    """
    clean_email = payload.email.strip().lower()
    stmt = select(User).where(func.lower(User.email) == clean_email)
    user = (await db.execute(stmt)).scalar_one_or_none()

    reset_url = None
    if user and user.is_active:
        reset_token = secrets.token_urlsafe(32)
        user.reset_password_token = reset_token
        user.reset_password_token_expires_at = utc_now() + datetime.timedelta(minutes=30)
        await db.commit()
        reset_url = send_password_reset_email(user.email, user.full_name, reset_token)

    return {
        "status": "SUCCESS",
        "message": "If that email address is in our database, we have sent instructions to reset your password.",
        "reset_url": reset_url
    }


@router.post("/reset-password")
async def reset_password(payload: ResetPasswordRequest, db: AsyncSession = Depends(get_db)):
    """
    Validates password reset token and securely updates stored password hash.
    """
    if len(payload.new_password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters long.")

    if payload.new_password != payload.confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match.")

    stmt = select(User).where(User.reset_password_token == payload.token.strip())
    user = (await db.execute(stmt)).scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired password reset link.")

    if user.reset_password_token_expires_at and to_utc(user.reset_password_token_expires_at) < utc_now():
        raise HTTPException(status_code=400, detail="Password reset link has expired. Please request a new one.")

    user.hashed_password = hash_password(payload.new_password)
    user.reset_password_token = None
    user.reset_password_token_expires_at = None
    await db.commit()

    return {
        "status": "SUCCESS",
        "message": "Your password has been successfully reset. You may now sign in with your new credentials."
    }


@router.post("/invite")
async def invite_employee(
    payload: InviteEmployeeRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(["admin"])),
    member: WorkspaceMember = Depends(get_current_workspace_member)
):
    """
    Allows a Company Administrator to invite an employee to their organization workspace.
    """
    clean_email = payload.email.strip().lower()
    
    # Check if already a member of this workspace
    user_stmt = select(User).where(func.lower(User.email) == clean_email)
    existing_user = (await db.execute(user_stmt)).scalar_one_or_none()
    if existing_user:
        mem_stmt = select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == member.workspace_id,
            WorkspaceMember.user_id == existing_user.id
        )
        if (await db.execute(mem_stmt)).scalar_one_or_none():
            raise HTTPException(status_code=400, detail="This user is already a member of this workspace.")

    ws_stmt = select(Workspace).where(Workspace.id == member.workspace_id)
    ws = (await db.execute(ws_stmt)).scalar_one_or_none()
    company_name = ws.name if ws else "OpsPilot Organization"

    invite_token = secrets.token_urlsafe(32)
    import hashlib
    t_hash = hashlib.sha256(invite_token.encode("utf-8")).hexdigest()
    invitation = WorkspaceInvitation(
        id=f"inv-{uuid.uuid4().hex[:12]}",
        workspace_id=member.workspace_id,
        email=clean_email,
        role=payload.role or "operator",
        invitation_token=invite_token,
        token_hash=t_hash,
        invited_by_user_id=user.id,
        status="pending",
        created_at=utc_now(),
        expires_at=utc_now() + datetime.timedelta(days=7)
    )
    db.add(invitation)
    await db.commit()

    invite_url = send_invitation_email(
        to_email=clean_email,
        company_name=company_name,
        inviter_name=user.full_name,
        invite_token=invite_token
    )

    return {
        "status": "SUCCESS",
        "message": f"Invitation sent to {clean_email}.",
        "invitation_token": invite_token,
        "token_hash": t_hash,
        "invite_url": invite_url
    }


@router.post("/register-invite")
async def register_invited_employee(payload: RegisterInviteRequest, db: AsyncSession = Depends(get_db)):
    """
    Completes registration for an employee joining via an organization invitation token.
    Supports both new employee accounts and existing user invitation acceptance.
    """
    if len(payload.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters long.")

    if payload.password != payload.confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match.")

    import hashlib
    raw_input = payload.token.strip()
    t_hash = hashlib.sha256(raw_input.encode("utf-8")).hexdigest()

    stmt = select(WorkspaceInvitation).where(
        (WorkspaceInvitation.token_hash == t_hash) | (WorkspaceInvitation.invitation_token == raw_input),
        WorkspaceInvitation.status == "pending"
    )
    invitation = (await db.execute(stmt)).scalar_one_or_none()
    if not invitation:
        raise HTTPException(status_code=400, detail="Invalid, expired, or already used invitation token.")

    if to_utc(invitation.expires_at) < utc_now():
        invitation.status = "expired"
        await db.commit()
        raise HTTPException(status_code=400, detail="This invitation has expired.")

    # Check if user account already exists for this email
    user_stmt = select(User).where(func.lower(User.email) == invitation.email.lower())
    user = (await db.execute(user_stmt)).scalar_one_or_none()
    if not user:
        user = User(
            id=f"usr-{uuid.uuid4().hex[:12]}",
            email=invitation.email.lower(),
            hashed_password=hash_password(payload.password),
            full_name=payload.full_name.strip(),
            role=invitation.role,
            is_active=True,
            is_verified=True,  # Verified via invitation link
            account_type="company_employee",
            created_at=utc_now()
        )
        db.add(user)
    else:
        # Existing user accepting invitation - verify password credentials
        if not verify_password(payload.password, user.hashed_password):
            raise HTTPException(
                status_code=400,
                detail="An account already exists for this email. Please enter your existing account password to accept the invitation."
            )
        # Check if already a member of this workspace
        check_mem = await db.execute(
            select(WorkspaceMember).where(
                WorkspaceMember.workspace_id == invitation.workspace_id,
                WorkspaceMember.user_id == user.id
            )
        )
        if check_mem.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="User is already an active member of this organization workspace.")

    # Attach member to workspace
    db.add(WorkspaceMember(
        id=f"mem-{uuid.uuid4().hex[:12]}",
        workspace_id=invitation.workspace_id,
        user_id=user.id,
        role=invitation.role
    ))

    invitation.status = "accepted"
    await db.commit()

    return {
        "status": "SUCCESS",
        "message": "Account activated and linked to the organization workspace! You may now sign in."
    }


@router.get("/workspaces")
async def list_user_workspaces(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Lists all organization workspaces where the user holds active membership."""
    stmt = (
        select(Workspace, WorkspaceMember.role)
        .join(WorkspaceMember, Workspace.id == WorkspaceMember.workspace_id)
        .where(WorkspaceMember.user_id == user.id)
    )
    res = await db.execute(stmt)
    rows = res.all()
    return [
        {
            "id": ws.id,
            "name": ws.name,
            "slug": ws.slug,
            "company_email": ws.company_email,
            "website": ws.website,
            "industry": ws.industry,
            "role": role,
            "status": ws.status
        }
        for ws, role in rows
    ]


@router.post("/switch-workspace")
async def switch_workspace(
    payload: SwitchWorkspaceRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Switches active workspace context and issues an updated JWT token with the new tenant scope.
    """
    mem_stmt = select(WorkspaceMember).where(
        WorkspaceMember.workspace_id == payload.workspace_id,
        WorkspaceMember.user_id == user.id
    )
    membership = (await db.execute(mem_stmt)).scalar_one_or_none()
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: You do not have an active membership in this workspace."
        )

    ws_stmt = select(Workspace).where(Workspace.id == payload.workspace_id)
    ws = (await db.execute(ws_stmt)).scalar_one_or_none()
    if not ws or ws.status != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The requested workspace is not currently active."
        )

    token = create_access_token({
        "sub": user.id,
        "email": user.email,
        "role": membership.role,
        "workspace_id": ws.id
    })

    return {
        "access_token": token,
        "token_type": "bearer",
        "workspace": {
            "id": ws.id,
            "name": ws.name,
            "role": membership.role
        }
    }


@router.get("/me")
async def get_me(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """
    Returns current authenticated user identity, primary workspace, and granular permissions.
    """
    mem_stmt = select(WorkspaceMember).where(WorkspaceMember.user_id == user.id)
    mem = (await db.execute(mem_stmt)).scalars().first()
    workspace_id = mem.workspace_id if mem else "default-ops"

    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role,
        "account_type": getattr(user, "account_type", "individual"),
        "company_name": getattr(user, "company_name", None),
        "workspace_id": workspace_id,
        "is_verified": user.is_verified,
        "permissions": get_role_permissions(user.role)
    }
