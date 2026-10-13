"""
Approval Center Endpoints
Enforces human authorization decisions, parameter verification, workspace isolation, and execution.
"""

import json
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.db import get_db
from app.auth.deps import get_current_user, require_role, get_current_workspace_member
from app.models.models import User, ApprovalRequest, WorkspaceMember
from app.schemas.schemas import ApprovalDecisionRequest
from app.approvals.approval_service import approval_service

router = APIRouter(prefix="/approvals", tags=["Approval Center"])

@router.get("")
async def list_approvals(
    status_filter: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    member: WorkspaceMember = Depends(get_current_workspace_member)
):
    query = (
        select(ApprovalRequest)
        .where(ApprovalRequest.workspace_id == member.workspace_id)
        .order_by(ApprovalRequest.created_at.desc())
    )
    if status_filter:
        query = query.where(ApprovalRequest.approval_status == status_filter)
    
    result = await db.execute(query)
    records = result.scalars().all()

    return [
        {
            "id": r.id,
            "execution_id": r.execution_id,
            "requesting_user_id": r.requesting_user_id,
            "target_system": r.target_system,
            "tool_name": r.tool_name,
            "action_summary": r.action_summary,
            "arguments": json.loads(r.canonical_action_arguments),
            "approval_status": r.approval_status,
            "created_at": r.created_at.isoformat() + "Z",
            "expires_at": r.expires_at.isoformat() + "Z",
            "approved_by": r.approved_by,
            "approved_at": r.approved_at.isoformat() + "Z" if r.approved_at else None,
            "execution_result": json.loads(r.execution_result) if r.execution_result else None
        }
        for r in records
    ]

@router.get("/{approval_id}")
async def get_approval(
    approval_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    member: WorkspaceMember = Depends(get_current_workspace_member)
):
    stmt = select(ApprovalRequest).where(
        ApprovalRequest.id == approval_id,
        ApprovalRequest.workspace_id == member.workspace_id
    )
    r = (await db.execute(stmt)).scalar_one_or_none()
    if not r:
        raise HTTPException(status_code=404, detail="Approval request not found or access denied")

    return {
        "id": r.id,
        "execution_id": r.execution_id,
        "target_system": r.target_system,
        "tool_name": r.tool_name,
        "action_summary": r.action_summary,
        "arguments": json.loads(r.canonical_action_arguments),
        "action_hash": r.action_hash,
        "approval_status": r.approval_status,
        "created_at": r.created_at.isoformat() + "Z",
        "expires_at": r.expires_at.isoformat() + "Z",
        "approved_by": r.approved_by,
        "execution_result": json.loads(r.execution_result) if r.execution_result else None
    }

@router.post("/{approval_id}/approve")
async def approve_request(
    approval_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(["admin", "operator"])),
    member: WorkspaceMember = Depends(get_current_workspace_member)
):
    """
    Approves the exact proposed write action and executes it with an issued cryptographic token.
    Enforces workspace membership and role restrictions.
    """
    # Verify approval exists and belongs to the caller's workspace
    check_stmt = select(ApprovalRequest).where(
        ApprovalRequest.id == approval_id,
        ApprovalRequest.workspace_id == member.workspace_id
    )
    req = (await db.execute(check_stmt)).scalar_one_or_none()
    if not req:
        raise HTTPException(status_code=404, detail="Approval request not found or unauthorized.")

    res = await approval_service.approve_and_execute(
        db=db,
        approval_id=approval_id,
        approver_user_id=user.id
    )
    if res.get("status") in ("ERROR", "SECURITY_ERROR"):
        raise HTTPException(status_code=400, detail=res.get("error"))
    return res

@router.post("/{approval_id}/reject")
async def reject_request(
    approval_id: str,
    payload: ApprovalDecisionRequest = ApprovalDecisionRequest(),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(["admin", "operator"])),
    member: WorkspaceMember = Depends(get_current_workspace_member)
):
    """
    Rejects the proposed write action. Guarantees no tool execution occurs.
    """
    check_stmt = select(ApprovalRequest).where(
        ApprovalRequest.id == approval_id,
        ApprovalRequest.workspace_id == member.workspace_id
    )
    req = (await db.execute(check_stmt)).scalar_one_or_none()
    if not req:
        raise HTTPException(status_code=404, detail="Approval request not found or unauthorized.")

    res = await approval_service.reject_request(
        db=db,
        approval_id=approval_id,
        user_id=user.id,
        reason=payload.reason
    )
    if res.get("status") == "ERROR":
        raise HTTPException(status_code=400, detail=res.get("error"))
    return res
