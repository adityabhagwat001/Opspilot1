"""
Company & Organization Management API Endpoints
Enforces Enterprise Administrator authorization for employee listing,
role promotion/demotion, member deactivation/removal, and invitation management.
Guarantees the sole remaining administrator cannot be removed or demoted.
"""

import datetime
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update, delete
from app.core.db import get_db
from app.models.models import User, Workspace, WorkspaceMember, WorkspaceInvitation, utc_now
from app.schemas.schemas import UpdateMemberRoleRequest
from app.auth.deps import get_current_user, require_role, get_current_workspace_member

router = APIRouter(prefix="/company", tags=["Company Management"])

@router.get("")
async def get_company_details(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(["admin"])),
    member: WorkspaceMember = Depends(get_current_workspace_member)
):
    """Returns active company organization workspace profile and member count."""
    ws = (await db.execute(select(Workspace).where(Workspace.id == member.workspace_id))).scalar_one_or_none()
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found.")

    member_count = await db.scalar(
        select(func.count(WorkspaceMember.id)).where(WorkspaceMember.workspace_id == member.workspace_id)
    ) or 0

    pending_invites_count = await db.scalar(
        select(func.count(WorkspaceInvitation.id)).where(
            WorkspaceInvitation.workspace_id == member.workspace_id,
            WorkspaceInvitation.status == "pending"
        )
    ) or 0

    return {
        "id": ws.id,
        "name": ws.name,
        "slug": ws.slug,
        "company_email": ws.company_email,
        "website": ws.website,
        "industry": ws.industry,
        "status": ws.status,
        "member_count": member_count,
        "pending_invites_count": pending_invites_count,
        "created_at": ws.created_at.isoformat() + "Z" if ws.created_at else None
    }


@router.get("/members")
async def list_company_members(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(["admin"])),
    member: WorkspaceMember = Depends(get_current_workspace_member)
):
    """Lists all active members enrolled in this company workspace."""
    stmt = (
        select(WorkspaceMember, User)
        .join(User, WorkspaceMember.user_id == User.id)
        .where(WorkspaceMember.workspace_id == member.workspace_id)
        .order_by(WorkspaceMember.role.asc(), User.full_name.asc())
    )
    results = (await db.execute(stmt)).all()

    return [
        {
            "member_id": mem.id,
            "user_id": u.id,
            "full_name": u.full_name,
            "email": u.email,
            "role": mem.role,
            "account_type": getattr(u, "account_type", "individual"),
            "account_status": getattr(u, "account_status", "active"),
            "is_verified": u.is_verified,
            "last_login_at": u.last_login_at.isoformat() + "Z" if u.last_login_at else None
        }
        for mem, u in results
    ]


@router.put("/members/{member_id}/role")
async def update_member_role(
    member_id: str,
    payload: UpdateMemberRoleRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(["admin"])),
    member: WorkspaceMember = Depends(get_current_workspace_member)
):
    """
    Updates an employee's role within the organization.
    Guarantees that the sole administrator cannot be demoted.
    """
    if payload.role not in ("admin", "operator"):
        raise HTTPException(status_code=400, detail="Role must be either 'admin' or 'operator'.")

    target_mem = (await db.execute(
        select(WorkspaceMember).where(
            WorkspaceMember.id == member_id,
            WorkspaceMember.workspace_id == member.workspace_id
        )
    )).scalar_one_or_none()

    if not target_mem:
        raise HTTPException(status_code=404, detail="Workspace member not found.")

    # Guardrail: Sole administrator protection
    if target_mem.role == "admin" and payload.role != "admin":
        admin_count = await db.scalar(
            select(func.count(WorkspaceMember.id)).where(
                WorkspaceMember.workspace_id == member.workspace_id,
                WorkspaceMember.role == "admin"
            )
        ) or 0
        if admin_count <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Security protection: Cannot demote the sole remaining administrator of the organization."
            )

    target_mem.role = payload.role
    await db.commit()

    return {
        "status": "SUCCESS",
        "message": f"Member role updated to {payload.role}.",
        "member_id": target_mem.id,
        "new_role": target_mem.role
    }


@router.delete("/members/{member_id}")
async def remove_member(
    member_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(["admin"])),
    member: WorkspaceMember = Depends(get_current_workspace_member)
):
    """
    Removes an employee from the organization workspace.
    Guarantees the sole administrator cannot be removed.
    """
    target_mem = (await db.execute(
        select(WorkspaceMember).where(
            WorkspaceMember.id == member_id,
            WorkspaceMember.workspace_id == member.workspace_id
        )
    )).scalar_one_or_none()

    if not target_mem:
        raise HTTPException(status_code=404, detail="Workspace member not found.")

    # Guardrail: Sole administrator protection
    if target_mem.role == "admin":
        admin_count = await db.scalar(
            select(func.count(WorkspaceMember.id)).where(
                WorkspaceMember.workspace_id == member.workspace_id,
                WorkspaceMember.role == "admin"
            )
        ) or 0
        if admin_count <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Security protection: Cannot remove the sole remaining administrator of the organization."
            )

    await db.delete(target_mem)
    await db.commit()

    return {
        "status": "SUCCESS",
        "message": "Employee successfully removed from the organization workspace."
    }


@router.get("/invitations")
async def list_pending_invitations(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(["admin"])),
    member: WorkspaceMember = Depends(get_current_workspace_member)
):
    """Lists all pending invitations issued for this workspace."""
    stmt = (
        select(WorkspaceInvitation)
        .where(
            WorkspaceInvitation.workspace_id == member.workspace_id,
            WorkspaceInvitation.status == "pending"
        )
        .order_by(WorkspaceInvitation.created_at.desc())
    )
    invites = (await db.execute(stmt)).scalars().all()

    return [
        {
            "id": inv.id,
            "email": inv.email,
            "role": inv.role,
            "status": inv.status,
            "created_at": inv.created_at.isoformat() + "Z",
            "expires_at": inv.expires_at.isoformat() + "Z"
        }
        for inv in invites
    ]


@router.delete("/invitations/{invitation_id}")
async def revoke_invitation(
    invitation_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(["admin"])),
    member: WorkspaceMember = Depends(get_current_workspace_member)
):
    """Revokes a pending employee invitation."""
    inv = (await db.execute(
        select(WorkspaceInvitation).where(
            WorkspaceInvitation.id == invitation_id,
            WorkspaceInvitation.workspace_id == member.workspace_id
        )
    )).scalar_one_or_none()

    if not inv:
        raise HTTPException(status_code=404, detail="Invitation not found.")

    inv.status = "revoked"
    await db.commit()

    return {
        "status": "SUCCESS",
        "message": f"Invitation to {inv.email} has been revoked."
    }

