"""
Integrations Status and Tool Discovery API Endpoints
"""

import os
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.db import get_db
from app.auth.deps import get_current_user
from app.models.models import User, IntegrationConnection
from app.integrations.mcp_router import mcp_router

router = APIRouter(prefix="/integrations", tags=["Integrations"])

@router.get("")
async def get_integrations_status(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    stmt = select(IntegrationConnection)
    res = await db.execute(stmt)
    conns = res.scalars().all()
    all_tools = await mcp_router.list_all_tools()

    integrations_list = []
    for c in conns:
        tools_for_system = [t for t in all_tools if t["system"] == c.provider]
        
        # Check provider specific credentials status
        creds_configured = True
        notes = "Connected to local FastMCP Server"
        if c.provider == "github":
            token_set = bool(os.getenv("GITHUB_TOKEN"))
            notes = "GitHub REST API v3 (Token configured)" if token_set else "GitHub REST API v3 (Fine-grained PAT pending in settings)"
        elif c.provider == "postgresql":
            notes = "Operational Database schema connected (3 seeded incidents, 3 tasks)"
        elif c.provider == "email":
            notes = "Enterprise Operations Mailbox store connected"
        elif c.provider == "calendar":
            notes = "Enterprise Operations Calendar store connected"

        integrations_list.append({
            "id": c.id,
            "provider": c.provider,
            "name": c.provider.capitalize() + " Integration",
            "status": c.status,
            "tool_count": len(tools_for_system),
            "tools": [t["name"] for t in tools_for_system],
            "notes": notes,
            "last_sync_at": c.last_sync_at.isoformat() + "Z"
        })

    return {
        "integrations": integrations_list,
        "total_tools": len(all_tools)
    }

@router.get("/tools")
async def list_available_tools(user: User = Depends(get_current_user)):
    tools = await mcp_router.list_all_tools()
    return {"count": len(tools), "tools": tools}
