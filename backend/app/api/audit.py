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
            "result_summary": l.result_summary,
            "status": l.status,
            "created_at": l.created_at.isoformat() + "Z"
        }
        for l in logs
    ]
