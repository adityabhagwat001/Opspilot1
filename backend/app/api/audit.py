"""
Enterprise Audit Log Endpoints
Enforces workspace isolation, search/filter, and comprehensive telemetry correlation.
"""

import json
from typing import Optional
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.db import get_db
from app.auth.deps import get_current_user, get_current_workspace_member
from app.models.models import User, AuditLog, WorkspaceMember

router = APIRouter(prefix="/audit", tags=["Audit Logs"])

@router.get("")
async def get_audit_logs(
    limit: int = 50,
    system_filter: Optional[str] = None,
    action_filter: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    member: WorkspaceMember = Depends(get_current_workspace_member)
):
    query = (
        select(AuditLog)
        .where(AuditLog.workspace_id == member.workspace_id)
        .order_by(AuditLog.created_at.desc())
        .limit(limit)
    )
    # Scope non-admin operators to their own activity records
    if user.role != "admin":
        query = query.where(AuditLog.user_id == user.id)

    if system_filter:
        query = query.where(AuditLog.target_system == system_filter)
    if action_filter:
        query = query.where(AuditLog.action_type == action_filter)

    res = await db.execute(query)
    logs = res.scalars().all()

    return [
        {
            "id": l.id,
            "user_id": l.user_id,
            "workspace_id": l.workspace_id,
            "execution_id": l.execution_id,
            "correlation_id": l.correlation_id,
            "action_type": l.action_type,
            "target_system": l.target_system,
            "tool_name": l.tool_name,
            "parameters": json.loads(l.parameters_json or "{}"),
            "approval_id": l.approval_id,
            "proposal_id": l.proposal_id,
            "failure_id": l.failure_id,
            "repo_full_name": l.repo_full_name,
            "has_solution": bool(
                l.solution_history_json or
                l.proposal_id or
                l.failure_id or
                (l.target_system == "github" and l.action_type in ("WRITE_EXECUTED", "WRITE_PROPOSED", "AI_ANALYSIS_COMPLETED", "FIX_PROPOSED", "RESOLUTION_VERIFIED"))
            ),
            "result_summary": l.result_summary,
            "status": l.status,
            "created_at": l.created_at.isoformat() + "Z"
        }
        for l in logs
    ]

@router.get("/{audit_id}/solution")
async def get_audit_solution(
    audit_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    member: WorkspaceMember = Depends(get_current_workspace_member)
):
    """
    Returns the comprehensive 8-part solution history for an audit log record.
    """
    from fastapi import HTTPException
    from app.services.solution_history_service import build_solution_history_payload
    from app.models.models import FixProposal, WorkflowFailure

    stmt = select(AuditLog).where(
        AuditLog.id == audit_id,
        AuditLog.workspace_id == member.workspace_id
    )
    if user.role != "admin":
        stmt = stmt.where(AuditLog.user_id == user.id)
    audit = (await db.execute(stmt)).scalar_one_or_none()
    if not audit:
        raise HTTPException(status_code=404, detail="Audit log record not found")

    # If already stored directly as JSON
    if audit.solution_history_json:
        try:
            return json.loads(audit.solution_history_json)
        except Exception:
            pass

    # Try resolving via proposal_id or approval_id or failure_id
    proposal = None
    if audit.proposal_id:
        p_stmt = select(FixProposal).where(FixProposal.id == audit.proposal_id)
        proposal = (await db.execute(p_stmt)).scalar_one_or_none()
    elif audit.approval_id:
        p_stmt = select(FixProposal).where(FixProposal.approval_id == audit.approval_id)
        proposal = (await db.execute(p_stmt)).scalar_one_or_none()

    failure = None
    if audit.failure_id:
        f_stmt = select(WorkflowFailure).where(WorkflowFailure.id == audit.failure_id)
        failure = (await db.execute(f_stmt)).scalar_one_or_none()
    elif proposal and proposal.failure_id:
        f_stmt = select(WorkflowFailure).where(WorkflowFailure.id == proposal.failure_id)
        failure = (await db.execute(f_stmt)).scalar_one_or_none()

    if proposal or failure:
        payload = await build_solution_history_payload(db, proposal=proposal, failure=failure)
        return payload

    raise HTTPException(status_code=404, detail="No solution history available for this audit record")

