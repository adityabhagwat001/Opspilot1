"""
OpsPilot Enterprise Human-in-the-Loop Approval Service
Enforces unbypassable approval boundaries before any write operation touches external systems.
Handles atomic approval transitions, cryptographic token issuing, execution verification,
single-use nonce consumption, and tamper-evident audit logging.
"""

import json
import uuid
import datetime
import logging
from typing import Optional, Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.models.models import ApprovalRequest, AuditLog, AgentExecution, ExecutionStep, ConsumedApprovalToken
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
        action_summary: str,
        target_resource: Optional[str] = None
    ) -> ApprovalRequest:
        """
        Creates a persisted, cryptographic pending approval request with a unique nonce.
        Pauses execution until explicit human authorization is granted.
        """
        now = datetime.datetime.now(datetime.timezone.utc)
        expires_at = now + datetime.timedelta(minutes=15)
        
        # Clean arguments from any previous token
        clean_args = {k: v for k, v in arguments.items() if k not in ("approval_token", "workspace_id")}
        action_hash = compute_action_hash(tool_name, clean_args)
        nonce = str(uuid.uuid4())

        approval = ApprovalRequest(
            execution_id=execution_id,
            requesting_user_id=user_id,
            workspace_id=workspace_id,
            target_system=target_system,
            tool_name=tool_name,
            target_resource=target_resource,
            canonical_action_arguments=json.dumps(clean_args, sort_keys=True),
            action_summary=action_summary,
            action_hash=action_hash,
            nonce=nonce,
            approval_status="pending",
            created_at=now,
            expires_at=expires_at
        )
        db.add(approval)

        # Audit proposal
        audit = AuditLog(
            user_id=user_id,
            workspace_id=workspace_id,
            execution_id=execution_id,
            action_type="WRITE_PROPOSED",
            target_system=target_system,
            tool_name=tool_name,
            parameters_json=json.dumps(clean_args, sort_keys=True),
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
        Atomically claims and approves a pending request:
        1. Atomic status transition: pending -> executing (prevents double-click race conditions)
        2. Validates expiration window
        3. Validates canonical parameters hash integrity
        4. Issues cryptographic single-use capability token bound to nonce
        5. Executes MCP tool
        6. Persists nonce to ConsumedApprovalToken table (replay immunity)
        7. Records truthful result status (failed vs succeeded) and audit trail
        """
        now = datetime.datetime.now(datetime.timezone.utc)

        # Atomic transition to executing state
        claim_stmt = (
            update(ApprovalRequest)
            .where(
                ApprovalRequest.id == approval_id,
                ApprovalRequest.approval_status == "pending"
            )
            .values(
                approval_status="executing",
                approved_by=approver_user_id,
                approved_at=now
            )
        )
        claim_result = await db.execute(claim_stmt)
        if claim_result.rowcount == 0:
            # Query current state to return actionable, accurate error
            stmt = select(ApprovalRequest).where(ApprovalRequest.id == approval_id)
            existing = (await db.execute(stmt)).scalar_one_or_none()
            if not existing:
                return {"status": "ERROR", "error": f"Approval request '{approval_id}' not found."}
            return {
                "status": "ERROR",
                "error": f"Cannot approve request in '{existing.approval_status}' state."
            }

        # Fetch claimed approval
        stmt = select(ApprovalRequest).where(ApprovalRequest.id == approval_id)
        approval = (await db.execute(stmt)).scalar_one()

        # Check expiration (15 minutes) - standardize naive datetime from SQLite to UTC
        exp = approval.expires_at
        if exp and exp.tzinfo is None:
            exp = exp.replace(tzinfo=datetime.timezone.utc)
        if exp and now > exp:
            approval.approval_status = "expired"
            await db.commit()
            return {
                "status": "ERROR",
                "error": "This approval request has expired (15 minute validity window exceeded)."
            }

        # Verify argument integrity against stored hash
        args = json.loads(approval.canonical_action_arguments)
        current_hash = compute_action_hash(approval.tool_name, args)
        if current_hash != approval.action_hash:
            approval.approval_status = "rejected"
            await db.commit()
            return {
                "status": "SECURITY_ERROR",
                "error": "Action parameters hash mismatch! Parameter tampering detected."
            }

        # Check if nonce was already consumed (defense in depth)
        nonce = approval.nonce or str(uuid.uuid4())
        nonce_check = await db.execute(
            select(ConsumedApprovalToken).where(ConsumedApprovalToken.nonce == nonce)
        )
        if nonce_check.scalar_one_or_none():
            approval.approval_status = "rejected"
            await db.commit()
            return {
                "status": "SECURITY_ERROR",
                "error": "Replay attack detected: approval nonce has already been consumed."
            }

        # Generate cryptographic 4-part single-use token issued by trusted backend
        approval_token = generate_approval_token(
            tool_name=approval.tool_name,
            arguments=args,
            workspace_id=approval.workspace_id,
            nonce=nonce
        )
        execution_args = {**args, "approval_token": approval_token}

        # Execute approved MCP tool
        try:
            execution_result = await mcp_router.execute_tool(approval.tool_name, execution_args)
            
            # Atomically mark nonce as consumed so it can NEVER be reused
            consumed_token = ConsumedApprovalToken(
                nonce=nonce,
                approval_id=approval.id,
                tool_name=approval.tool_name,
                workspace_id=approval.workspace_id,
                action_hash=approval.action_hash,
                consumed_at=now
            )
            db.add(consumed_token)

            # Check truthful execution outcome
            is_failed = False
            if isinstance(execution_result, dict):
                if not execution_result.get("success", True) or execution_result.get("status") in ("FAILED", "ERROR") or "error" in execution_result:
                    is_failed = True

            approval.approval_status = "failed" if is_failed else "succeeded"
            approval.execution_result = json.dumps(execution_result)
            
            # Audit log
            audit = AuditLog(
                user_id=approver_user_id,
                workspace_id=approval.workspace_id,
                execution_id=approval.execution_id,
                action_type="WRITE_EXECUTED",
                target_system=approval.target_system,
                tool_name=approval.tool_name,
                parameters_json=approval.canonical_action_arguments,
                approval_id=approval.id,
                result_summary=f"Executed with status: {'FAILED' if is_failed else 'SUCCESS'}",
                status="failure" if is_failed else "success"
            )
            db.add(audit)

            # Update Agent Execution
            exec_stmt = select(AgentExecution).where(AgentExecution.id == approval.execution_id)
            execution = (await db.execute(exec_stmt)).scalar_one_or_none()
            if execution:
                execution.status = "failed" if is_failed else "completed"
                execution.current_step = f"Executed write action: {approval.tool_name} ({'FAILED' if is_failed else 'SUCCESS'})"
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
                "status": "FAILED" if is_failed else "SUCCESS",
                "approval_id": approval_id,
                "tool_name": approval.tool_name,
                "target_system": approval.target_system,
                "execution_result": execution_result
            }
        except Exception as ex:
            logger.error(f"Failed to execute approved write tool: {ex}", exc_info=True)
            approval.approval_status = "failed"
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
        Atomically rejects a proposed write action. Guarantees no tool execution occurs.
        """
        now = datetime.datetime.now(datetime.timezone.utc)
        
        claim_stmt = (
            update(ApprovalRequest)
            .where(
                ApprovalRequest.id == approval_id,
                ApprovalRequest.approval_status == "pending"
            )
            .values(
                approval_status="rejected",
                approved_by=user_id,
                approved_at=now,
                execution_result=json.dumps({"rejected": True, "reason": reason or "Rejected by human operator."})
            )
        )
        result = await db.execute(claim_stmt)
        if result.rowcount == 0:
            stmt = select(ApprovalRequest).where(ApprovalRequest.id == approval_id)
            existing = (await db.execute(stmt)).scalar_one_or_none()
            if not existing:
                return {"status": "ERROR", "error": f"Approval request '{approval_id}' not found."}
            return {"status": "ERROR", "error": f"Request is already in '{existing.approval_status}' state."}

        stmt = select(ApprovalRequest).where(ApprovalRequest.id == approval_id)
        approval = (await db.execute(stmt)).scalar_one()

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
            execution_id=approval.execution_id,
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
