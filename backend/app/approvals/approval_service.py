"""
OpsPilot Enterprise Human-in-the-Loop Approval Service
Enforces unbypassable approval boundaries before any write operation touches external systems.
Handles atomic approval transitions, cryptographic token issuing, execution verification, and audit logging.
"""

import json
import datetime
import logging
from typing import Optional, Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.models.models import ApprovalRequest, AuditLog, AgentExecution, ExecutionStep
from app.core.security import compute_action_hash, generate_approval_token
from app.integrations.mcp_router import mcp_router

logger = logging.getLogger("opspilot.approvals")

class ApprovalService:
    async def create_approval_request(
        self,
        db: AsyncSession,
        execution_id: str,
        user_id: str,
        workspace_id: str,
        target_system: str,
        tool_name: str,
        arguments: Dict[str, Any],
        action_summary: str
    ) -> ApprovalRequest:
        """
        Creates a persisted, cryptographic pending approval request.
        Pauses execution until explicit human authorization is granted.
        """
        now = datetime.datetime.now(datetime.timezone.utc)
        expires_at = now + datetime.timedelta(minutes=15)
        
        # Clean arguments from any previous token
        clean_args = {k: v for k, v in arguments.items() if k != "approval_token"}
        action_hash = compute_action_hash(tool_name, clean_args)

        approval = ApprovalRequest(
            execution_id=execution_id,
            requesting_user_id=user_id,
            workspace_id=workspace_id,
            target_system=target_system,
            tool_name=tool_name,
            canonical_action_arguments=json.dumps(clean_args, sort_keys=True),
            action_summary=action_summary,
            action_hash=action_hash,
            approval_status="pending",
            created_at=now,
            expires_at=expires_at
        )
        db.add(approval)

        # Audit proposal
        audit = AuditLog(
            user_id=user_id,
            workspace_id=workspace_id,
            action_type="WRITE_PROPOSED",
            target_system=target_system,
            tool_name=tool_name,
            parameters_json=json.dumps(clean_args),
            approval_id=approval.id,
            result_summary=f"Proposed write action awaiting human review: {action_summary}",
            status="pending"
        )
        db.add(audit)

        # Update execution state
        exec_stmt = select(AgentExecution).where(AgentExecution.id == execution_id)
        execution = (await db.execute(exec_stmt)).scalar_one_or_none()
        if execution:
            execution.status = "awaiting_approval"
            execution.current_step = f"Awaiting approval for {tool_name}"

        await db.commit()
        await db.refresh(approval)
        return approval

    async def approve_and_execute(
        self,
        db: AsyncSession,
        approval_id: str,
        approver_user_id: str
    ) -> Dict[str, Any]:
        """
        Atomically approves a pending request, verifies parameters integrity,
        generates the unforgeable approval token, executes the MCP tool, and records audit trail.
        """
        stmt = select(ApprovalRequest).where(ApprovalRequest.id == approval_id)
        approval = (await db.execute(stmt)).scalar_one_or_none()
        
        if not approval:
            return {"status": "ERROR", "error": f"Approval request '{approval_id}' not found."}

        # Check atomic status
        if approval.approval_status != "pending":
            return {
                "status": "ERROR",
                "error": f"Cannot approve request in '{approval.approval_status}' state."
            }

        now = datetime.datetime.now(datetime.timezone.utc)
        if now > approval.expires_at:
            approval.approval_status = "expired"
            await db.commit()
            return {"status": "ERROR", "error": "This approval request has expired (15 minute validity window exceeded)."}

        # Verify argument integrity
        args = json.loads(approval.canonical_action_arguments)
        current_hash = compute_action_hash(approval.tool_name, args)
        if current_hash != approval.action_hash:
            approval.approval_status = "rejected"
            await db.commit()
            return {"status": "SECURITY_ERROR", "error": "Action parameters hash mismatch! Parameter tampering detected."}

        # Transition status to approved
        approval.approval_status = "approved"
        approval.approved_by = approver_user_id
        approval.approved_at = now

        # Generate cryptographic token issued by trusted backend
        approval_token = generate_approval_token(approval.tool_name, args)
        execution_args = {**args, "approval_token": approval_token}

        # Execute approved MCP tool
        try:
            execution_result = await mcp_router.execute_tool(approval.tool_name, execution_args)
            approval.execution_result = json.dumps(execution_result)
            
            # Audit log
            audit = AuditLog(
                user_id=approver_user_id,
                workspace_id=approval.workspace_id,
                action_type="WRITE_EXECUTED",
                target_system=approval.target_system,
                tool_name=approval.tool_name,
                parameters_json=approval.canonical_action_arguments,
                approval_id=approval.id,
                result_summary=f"Executed with result status: {execution_result.get('status', 'SUCCESS')}",
                status="success" if execution_result.get("status") != "FAILED" else "failure"
            )
            db.add(audit)

            # Update Agent Execution
            exec_stmt = select(AgentExecution).where(AgentExecution.id == approval.execution_id)
            execution = (await db.execute(exec_stmt)).scalar_one_or_none()
            if execution:
                execution.status = "completed"
                execution.current_step = f"Completed approved write action: {approval.tool_name}"
                completed = json.loads(execution.completed_actions_json or "[]")
                completed.append({
                    "tool": approval.tool_name,
                    "result": execution_result,
                    "approved_by": approver_user_id,
                    "timestamp": now.isoformat() + "Z"
                })
                execution.completed_actions_json = json.dumps(completed)

            await db.commit()
            return {
                "status": "SUCCESS",
                "approval_id": approval_id,
                "tool_name": approval.tool_name,
                "target_system": approval.target_system,
                "execution_result": execution_result
            }
        except Exception as ex:
            logger.error(f"Failed to execute approved write tool: {ex}", exc_info=True)
            approval.execution_result = json.dumps({"error": str(ex), "status": "FAILED"})
            await db.commit()
            return {"status": "FAILED", "error": str(ex)}

    async def reject_request(
        self,
        db: AsyncSession,
        approval_id: str,
        user_id: str,
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Rejects a proposed write action. Guarantees no tool execution occurs.
        """
        stmt = select(ApprovalRequest).where(ApprovalRequest.id == approval_id)
        approval = (await db.execute(stmt)).scalar_one_or_none()
        if not approval:
            return {"status": "ERROR", "error": f"Approval request '{approval_id}' not found."}

        if approval.approval_status != "pending":
            return {"status": "ERROR", "error": f"Request is already in '{approval.approval_status}' state."}

        approval.approval_status = "rejected"
        approval.approved_by = user_id
        approval.approved_at = datetime.datetime.now(datetime.timezone.utc)
        approval.execution_result = json.dumps({"rejected": True, "reason": reason or "Rejected by user."})

        # Update Agent Execution
        exec_stmt = select(AgentExecution).where(AgentExecution.id == approval.execution_id)
        execution = (await db.execute(exec_stmt)).scalar_one_or_none()
        if execution:
            execution.status = "rejected"
            execution.current_step = f"Write rejected by human approver: {approval.tool_name}"

        # Audit log
        audit = AuditLog(
            user_id=user_id,
            workspace_id=approval.workspace_id,
            action_type="APPROVAL_REJECTED",
            target_system=approval.target_system,
            tool_name=approval.tool_name,
            parameters_json=approval.canonical_action_arguments,
            approval_id=approval.id,
            result_summary=f"Action rejected by user: {reason or 'No reason provided'}",
            status="rejected"
        )
        db.add(audit)
        await db.commit()

        return {
            "status": "REJECTED",
            "approval_id": approval_id,
            "message": "Action has been rejected. External system was not modified."
        }

approval_service = ApprovalService()
