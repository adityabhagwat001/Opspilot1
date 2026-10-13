"""
Dashboard Stats API Endpoint
Enforces workspace isolation, truthful connection state counts, and real-time operations summary.
"""

import json
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.core.db import get_db
from app.auth.deps import get_current_user, get_current_workspace_member
from app.models.models import User, IntegrationConnection, ApprovalRequest, AuditLog, WorkspaceMember
from app.integrations.mcp_router import mcp_router

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

@router.get("/stats")
async def get_dashboard_stats(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    member: WorkspaceMember = Depends(get_current_workspace_member)
):
    ws_id = member.workspace_id

    # 1. Integrations status for workspace
    conns_res = await db.execute(
        select(IntegrationConnection).where(IntegrationConnection.workspace_id == ws_id)
    )
    connections = conns_res.scalars().all()
    
    # 2. Pending approvals count for workspace
    pending_approvals_count = await db.scalar(
        select(func.count())
        .select_from(ApprovalRequest)
        .where(
            ApprovalRequest.workspace_id == ws_id,
            ApprovalRequest.approval_status == "pending"
        )
    ) or 0

    # 3. Recent audit logs for workspace
    recent_audit_res = await db.execute(
        select(AuditLog)
        .where(AuditLog.workspace_id == ws_id)
        .order_by(AuditLog.created_at.desc())
        .limit(10)
    )
    recent_logs = recent_audit_res.scalars().all()

    # 4. Operations summary from FastMCP
    ops_summary = await mcp_router.execute_tool("get_operations_summary", {"workspace_id": ws_id})

    all_tools = await mcp_router.list_all_tools()

    return {
        "user": {"name": user.full_name, "role": user.role},
        "workspace_id": ws_id,
        "connected_systems": len(connections),
        "total_mcp_tools": len(all_tools),
        "pending_approvals": pending_approvals_count,
        "operations": ops_summary.get("data") if isinstance(ops_summary, dict) and "data" in ops_summary else ops_summary,
        "recent_activity": [
            {
                "id": log.id,
                "action_type": log.action_type,
                "target_system": log.target_system,
                "tool_name": log.tool_name,
                "summary": log.result_summary,
                "status": log.status,
                "created_at": log.created_at.isoformat() + "Z"
            }
            for log in recent_logs
        ]
    }
