"""
AI Assistant Chat and Real-time Execution Streaming Endpoints
"""

import json
import asyncio
import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.db import get_db
from app.auth.deps import get_current_user
from app.models.models import (
    User,
    AgentConversation,
    AgentMessage,
    AgentExecution,
    ExecutionStep,
    ApprovalRequest
)
from app.schemas.schemas import ChatMessageRequest
from app.agents.agent_graph import agent_executor
from app.approvals.approval_service import approval_service

router = APIRouter(prefix="/chat", tags=["AI Assistant"])

@router.get("/conversations")
async def list_conversations(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    stmt = (
        select(AgentConversation)
        .where(AgentConversation.user_id == user.id)
        .order_by(AgentConversation.updated_at.desc())
    )
    result = await db.execute(stmt)
    convs = result.scalars().all()
    return [
        {
            "id": c.id,
            "title": c.title,
            "created_at": c.created_at.isoformat() + "Z",
            "updated_at": c.updated_at.isoformat() + "Z"
        }
        for c in convs
    ]

@router.get("/conversations/{conversation_id}/messages")
async def get_messages(
    conversation_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    stmt = (
        select(AgentMessage)
        .where(AgentMessage.conversation_id == conversation_id)
        .order_by(AgentMessage.created_at.asc())
    )
    result = await db.execute(stmt)
    msgs = result.scalars().all()
    return [
        {
            "id": m.id,
            "role": m.role,
            "content": m.content,
            "tool_calls": json.loads(m.tool_calls_json or "[]"),
            "tool_results": json.loads(m.tool_results_json or "[]"),
            "created_at": m.created_at.isoformat() + "Z"
        }
        for m in msgs
    ]

@router.post("/message")
async def send_message(
    payload: ChatMessageRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    now = datetime.datetime.utcnow()

    # 1. Resolve or create conversation
    conv_id = payload.conversation_id
    if not conv_id:
        conv = AgentConversation(
            user_id=user.id,
            title=payload.message[:50] + ("..." if len(payload.message) > 50 else "")
        )
        db.add(conv)
        await db.commit()
        await db.refresh(conv)
        conv_id = conv.id

    # 2. Save user message
    user_msg = AgentMessage(
        conversation_id=conv_id,
        role="user",
        content=payload.message
    )
    db.add(user_msg)

    # 3. Create Agent Execution record
    execution = AgentExecution(
        conversation_id=conv_id,
        user_id=user.id,
        user_request=payload.message,
        status="running",
        current_step="Analyzing request"
    )
    db.add(execution)
    await db.commit()
    await db.refresh(execution)

    # 4. Invoke LangGraph Agent Graph
    agent_input = {
        "execution_id": execution.id,
        "user_id": user.id,
        "workspace_id": "default-ops",
        "user_request": payload.message,
        "conversation_history": [],
        "target_systems": [],
        "available_tools": [],
        "planned_actions": [],
        "completed_actions": [],
        "pending_approval": None,
        "tool_results": [],
        "final_response": None,
        "execution_status": "received",
        "current_step": "started",
        "errors": []
    }

    graph_result = await agent_executor.ainvoke(agent_input)

    # 5. Handle write approval requirement
    pending_appr = graph_result.get("pending_approval")
    approval_rec = None
    if pending_appr:
        approval_rec = await approval_service.create_approval_request(
            db=db,
            execution_id=execution.id,
            user_id=user.id,
            workspace_id="default-ops",
            target_system=pending_appr["target_system"],
            tool_name=pending_appr["tool_name"],
            arguments=pending_appr["arguments"],
            action_summary=pending_appr["action_summary"]
        )

    # 6. Save Assistant response message
    asst_msg = AgentMessage(
        conversation_id=conv_id,
        role="assistant",
        content=graph_result.get("final_response") or "Processing completed.",
        tool_calls_json=json.dumps(graph_result.get("planned_actions", [])),
        tool_results_json=json.dumps(graph_result.get("tool_results", []))
    )
    db.add(asst_msg)

    # 7. Update Execution record
    execution.status = graph_result.get("execution_status", "completed")
    execution.current_step = graph_result.get("current_step", "completed")
    execution.planned_actions_json = json.dumps(graph_result.get("planned_actions", []))
    execution.completed_actions_json = json.dumps(graph_result.get("completed_actions", []))
    execution.final_response = graph_result.get("final_response")
    await db.commit()

    return {
        "conversation_id": conv_id,
        "execution_id": execution.id,
        "status": execution.status,
        "response": execution.final_response,
        "planned_actions": graph_result.get("planned_actions", []),
        "tool_results": graph_result.get("tool_results", []),
        "pending_approval": {
            "id": approval_rec.id,
            "target_system": approval_rec.target_system,
            "tool_name": approval_rec.tool_name,
            "action_summary": approval_rec.action_summary,
            "arguments": json.loads(approval_rec.canonical_action_arguments),
            "expires_at": approval_rec.expires_at.isoformat() + "Z"
        } if approval_rec else None
    }

@router.get("/executions/{execution_id}/stream")
async def stream_execution_progress(
    execution_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """
    Server-Sent Events (SSE) streaming real execution status from database.
    """
    async def event_generator():
        last_step = ""
        for _ in range(30):  # Stream updates up to 30 intervals
            stmt = select(AgentExecution).where(AgentExecution.id == execution_id)
            exec_rec = (await db.execute(stmt)).scalar_one_or_none()
            if not exec_rec:
                yield f"data: {json.dumps({'error': 'Execution not found'})}\n\n"
                break

            if exec_rec.current_step != last_step or exec_rec.status in ("completed", "awaiting_approval", "rejected", "failed"):
                last_step = exec_rec.current_step
                payload = {
                    "execution_id": exec_rec.id,
                    "status": exec_rec.status,
                    "current_step": exec_rec.current_step,
                    "updated_at": exec_rec.updated_at.isoformat() + "Z"
                }
                yield f"data: {json.dumps(payload)}\n\n"

            if exec_rec.status in ("completed", "awaiting_approval", "rejected", "failed"):
                break

            await asyncio.sleep(1)

    return StreamingResponse(event_generator(), media_type="text/event-stream")
