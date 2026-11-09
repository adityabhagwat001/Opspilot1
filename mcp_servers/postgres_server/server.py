"""
OpsPilot Custom FastMCP Server: PostgreSQL Operations Integration.
Implements Model Context Protocol (MCP) using FastMCP with strict human approval enforcement.
Exposes read tools for authorized operational queries and protected write tools requiring valid approval tokens.
Read tools perform ZERO schema mutations or fixture seeding.
"""

import os
import sys
import hmac
import hashlib
import json
import uuid
import datetime
from typing import Optional, Dict, Any, List
from fastmcp import FastMCP
from sqlalchemy import select, update, insert

# Add parent directory to path so imports work seamlessly
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from db import (
    ops_db,
    OperationalIncident,
    OperationalTask,
    DatabaseEntity,
    utc_now,
)
from envelope import create_success_envelope, create_error_envelope

# Initialize FastMCP Server
mcp = FastMCP("opspilot-postgres-server")

# Shared backend secret for approval token verification
APPROVAL_SECRET = os.getenv("OPSPILOT_APPROVAL_SECRET", "opspilot_trusted_approval_boundary_secret_key_32chars")

def compute_action_hash(tool_name: str, arguments: Dict[str, Any]) -> str:
    clean_args = {k: v for k, v in arguments.items() if k not in ("approval_token", "workspace_id")}
    canonical = f"{tool_name}:{json.dumps(clean_args, sort_keys=True)}"
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

def verify_approval_token(
    tool_name: str,
    args: Dict[str, Any],
    approval_token: str,
    workspace_id: str = "default-ops"
) -> bool:
    """
    Verifies that the approval token was cryptographically signed by the OpsPilot backend
    for this EXACT tool, workspace, and CANONICAL arguments payload.
    The LLM cannot forge this token.
    """
    if not approval_token:
        return False
    try:
        # Token format: nonce.timestamp.action_hash.signature
        parts = approval_token.split(".")
        if len(parts) != 4:
            return False
        nonce, timestamp_str, token_action_hash, signature = parts
        
        # Check token expiration (15 minutes)
        token_time = int(timestamp_str)
        now = int(datetime.datetime.now(datetime.timezone.utc).timestamp())
        if now - token_time > 900 or token_time - now > 60:
            return False

        # Validate arguments integrity: actual arguments MUST match token hash
        actual_hash = compute_action_hash(tool_name, args)
        if not hmac.compare_digest(actual_hash, token_action_hash):
            # Check with None values stripped in case caller omitted optional parameters
            stripped_args = {k: v for k, v in args.items() if v is not None}
            stripped_hash = compute_action_hash(tool_name, stripped_args)
            if not hmac.compare_digest(stripped_hash, token_action_hash):
                return False

        # Validate HMAC signature
        canonical = f"{tool_name}:{workspace_id}:{nonce}:{timestamp_str}:{token_action_hash}"
        expected_sig = hmac.new(
            APPROVAL_SECRET.encode("utf-8"),
            canonical.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(signature, expected_sig)
    except Exception:
        return False

# =========================================================================
# READ TOOLS (Authorized operational queries - ZERO DDL / Seeding)
# =========================================================================

@mcp.tool()
async def list_database_entities(workspace_id: str = "default-ops") -> Dict[str, Any]:
    """
    List authorized operational database entities, tables, caches, and clusters in the workspace.
    Returns status, record counts, region, and operational health.
    """
    try:
        async with ops_db.session_factory() as session:
            stmt = select(DatabaseEntity).where(DatabaseEntity.workspace_id == workspace_id)
            result = await session.execute(stmt)
            entities = result.scalars().all()
            data = [
                {
                    "name": e.name,
                    "entity_type": e.entity_type,
                    "status": e.status,
                    "region": e.region,
                    "description": e.description,
                    "record_count": e.record_count,
                }
                for e in entities
            ]
            return create_success_envelope(
                system="postgresql",
                tool="list_database_entities",
                data=data,
                resource_ids_urls=[e.name for e in entities]
            )
    except Exception as ex:
        return create_error_envelope(
            system="postgresql",
            tool="list_database_entities",
            error=str(ex),
            error_category="DATABASE_QUERY_ERROR",
            retryable=True
        )

@mcp.tool()
async def get_operations_summary(workspace_id: str = "default-ops") -> Dict[str, Any]:
    """
    Get executive summary of operational incidents, active remediation tasks, and service health.
    """
    try:
        async with ops_db.session_factory() as session:
            incidents_result = await session.execute(
                select(OperationalIncident).where(OperationalIncident.workspace_id == workspace_id)
            )
            incidents = incidents_result.scalars().all()

            tasks_result = await session.execute(
                select(OperationalTask).where(OperationalTask.workspace_id == workspace_id)
            )
            tasks = tasks_result.scalars().all()

            open_incidents = [i for i in incidents if i.status in ("open", "investigating")]
            critical_count = len([i for i in open_incidents if i.severity == "critical"])
            pending_tasks = [t for t in tasks if t.status in ("pending", "in_progress")]

            summary = {
                "workspace_id": workspace_id,
                "total_incidents": len(incidents),
                "open_incidents": len(open_incidents),
                "critical_incidents": critical_count,
                "total_tasks": len(tasks),
                "active_tasks": len(pending_tasks),
                "system_status": "degraded" if critical_count > 0 else "healthy",
                "last_checked": datetime.datetime.now(datetime.timezone.utc).isoformat() + "Z",
            }
            return create_success_envelope(
                system="postgresql",
                tool="get_operations_summary",
                data=summary
            )
    except Exception as ex:
        return create_error_envelope(
            system="postgresql",
            tool="get_operations_summary",
            error=str(ex),
            error_category="DATABASE_QUERY_ERROR",
            retryable=True
        )

@mcp.tool()
async def list_incidents(
    status: Optional[str] = None,
    severity: Optional[str] = None,
    workspace_id: str = "default-ops"
) -> Dict[str, Any]:
    """
    Retrieve live operational incidents filtered by status (open, investigating, mitigated, resolved)
    or severity (critical, high, medium, low).
    """
    try:
        async with ops_db.session_factory() as session:
            query = select(OperationalIncident).where(OperationalIncident.workspace_id == workspace_id)
            if status:
                query = query.where(OperationalIncident.status == status)
            if severity:
                query = query.where(OperationalIncident.severity == severity)
            
            query = query.order_by(OperationalIncident.created_at.desc())
            result = await session.execute(query)
            incidents = result.scalars().all()

            data = [
                {
                    "id": inc.id,
                    "title": inc.title,
                    "severity": inc.severity,
                    "status": inc.status,
                    "service": inc.service,
                    "description": inc.description,
                    "assigned_to": inc.assigned_to,
                    "created_at": inc.created_at.isoformat() if inc.created_at else None,
                    "updated_at": inc.updated_at.isoformat() if inc.updated_at else None,
                }
                for inc in incidents
            ]
            return create_success_envelope(
                system="postgresql",
                tool="list_incidents",
                data=data,
                resource_ids_urls=[inc.id for inc in incidents]
            )
    except Exception as ex:
        return create_error_envelope(
            system="postgresql",
            tool="list_incidents",
            error=str(ex),
            error_category="DATABASE_QUERY_ERROR",
            retryable=True
        )

@mcp.tool()
async def get_incident_details(incident_id: str, workspace_id: str = "default-ops") -> Dict[str, Any]:
    """
    Get full details for a specific operational incident along with linked remediation tasks.
    """
    try:
        async with ops_db.session_factory() as session:
            inc_stmt = select(OperationalIncident).where(
                OperationalIncident.id == incident_id,
                OperationalIncident.workspace_id == workspace_id
            )
            inc_res = await session.execute(inc_stmt)
            incident = inc_res.scalar_one_or_none()
            if not incident:
                return create_error_envelope(
                    system="postgresql",
                    tool="get_incident_details",
                    error=f"Incident '{incident_id}' not found in workspace '{workspace_id}'",
                    error_category="NOT_FOUND"
                )

            tasks_stmt = select(OperationalTask).where(
                OperationalTask.incident_id == incident_id,
                OperationalTask.workspace_id == workspace_id
            )
            tasks_res = await session.execute(tasks_stmt)
            tasks = tasks_res.scalars().all()

            data = {
                "id": incident.id,
                "title": incident.title,
                "severity": incident.severity,
                "status": incident.status,
                "service": incident.service,
                "description": incident.description,
                "assigned_to": incident.assigned_to,
                "created_at": incident.created_at.isoformat() if incident.created_at else None,
                "updated_at": incident.updated_at.isoformat() if incident.updated_at else None,
                "linked_tasks": [
                    {
                        "id": t.id,
                        "title": t.title,
                        "status": t.status,
                        "priority": t.priority,
                        "assignee": t.assignee
                    }
                    for t in tasks
                ]
            }
            return create_success_envelope(
                system="postgresql",
                tool="get_incident_details",
                data=data,
                resource_ids_urls=[incident.id]
            )
    except Exception as ex:
        return create_error_envelope(
            system="postgresql",
            tool="get_incident_details",
            error=str(ex),
            error_category="DATABASE_QUERY_ERROR"
        )

@mcp.tool()
async def list_operational_tasks(
    status: Optional[str] = None,
    incident_id: Optional[str] = None,
    workspace_id: str = "default-ops"
) -> Dict[str, Any]:
    """
    Retrieve operational tasks filtered by status or linked incident.
    """
    try:
        async with ops_db.session_factory() as session:
            query = select(OperationalTask).where(OperationalTask.workspace_id == workspace_id)
            if status:
                query = query.where(OperationalTask.status == status)
            if incident_id:
                query = query.where(OperationalTask.incident_id == incident_id)

            query = query.order_by(OperationalTask.created_at.desc())
            result = await session.execute(query)
            tasks = result.scalars().all()

            data = [
                {
                    "id": t.id,
                    "incident_id": t.incident_id,
                    "title": t.title,
                    "description": t.description,
                    "status": t.status,
                    "priority": t.priority,
                    "assignee": t.assignee,
                    "created_at": t.created_at.isoformat() if t.created_at else None,
                    "updated_at": t.updated_at.isoformat() if t.updated_at else None,
                }
                for t in tasks
            ]
            return create_success_envelope(
                system="postgresql",
                tool="list_operational_tasks",
                data=data,
                resource_ids_urls=[t.id for t in tasks]
            )
    except Exception as ex:
        return create_error_envelope(
            system="postgresql",
            tool="list_operational_tasks",
            error=str(ex),
            error_category="DATABASE_QUERY_ERROR"
        )

@mcp.tool()
async def get_task_details(task_id: str, workspace_id: str = "default-ops") -> Dict[str, Any]:
    """
    Get full details of a specific operational task.
    """
    try:
        async with ops_db.session_factory() as session:
            stmt = select(OperationalTask).where(
                OperationalTask.id == task_id,
                OperationalTask.workspace_id == workspace_id
            )
            res = await session.execute(stmt)
            task = res.scalar_one_or_none()
            if not task:
                return create_error_envelope(
                    system="postgresql",
                    tool="get_task_details",
                    error=f"Task '{task_id}' not found in workspace '{workspace_id}'",
                    error_category="NOT_FOUND"
                )
            
            data = {
                "id": task.id,
                "incident_id": task.incident_id,
                "title": task.title,
                "description": task.description,
                "status": task.status,
                "priority": task.priority,
                "assignee": task.assignee,
                "created_at": task.created_at.isoformat() if task.created_at else None,
                "updated_at": task.updated_at.isoformat() if task.updated_at else None,
            }
            return create_success_envelope(
                system="postgresql",
                tool="get_task_details",
                data=data,
                resource_ids_urls=[task.id]
            )
    except Exception as ex:
        return create_error_envelope(
            system="postgresql",
            tool="get_task_details",
            error=str(ex),
            error_category="DATABASE_QUERY_ERROR"
        )

# =========================================================================
# WRITE TOOLS (Mandatory Human Approval Gate)
# =========================================================================

@mcp.tool()
async def create_operational_task(
    title: str,
    description: str,
    priority: str = "p1",
    incident_id: Optional[str] = None,
    assignee: Optional[str] = None,
    approval_token: str = "",
    workspace_id: str = "default-ops"
) -> Dict[str, Any]:
    """
    [WRITE OPERATION - REQUIRES APPROVAL]
    Create a new operational task in the database.
    Requires a cryptographic approval_token from the OpsPilot backend approval boundary.
    """
    call_args = {
        "title": title,
        "description": description,
        "priority": priority,
        "incident_id": incident_id,
        "assignee": assignee,
    }

    if not verify_approval_token("create_operational_task", call_args, approval_token, workspace_id):
        return create_error_envelope(
            system="postgresql",
            tool="create_operational_task",
            error="WRITE_APPROVAL_REQUIRED: This write operation modifies operational records and requires explicit human approval.",
            error_category="APPROVAL_REQUIRED",
            is_write=True
        )

    task_id = f"TSK-{uuid.uuid4().hex[:6].upper()}"
    new_task = OperationalTask(
        id=task_id,
        incident_id=incident_id,
        title=title,
        description=description,
        status="pending",
        priority=priority,
        assignee=assignee,
        workspace_id=workspace_id,
        created_at=utc_now(),
        updated_at=utc_now()
    )

    async with ops_db.session_factory() as session:
        session.add(new_task)
        await session.commit()

    return create_success_envelope(
        system="postgresql",
        tool="create_operational_task",
        data={
            "action": "created_operational_task",
            "task_id": task_id,
            "title": title,
            "priority": priority,
            "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat() + "Z"
        },
        is_write=True,
        resource_ids_urls=[task_id]
    )

@mcp.tool()
async def update_operational_task(
    task_id: str,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    assignee: Optional[str] = None,
    approval_token: str = "",
    workspace_id: str = "default-ops"
) -> Dict[str, Any]:
    """
    [WRITE OPERATION - REQUIRES APPROVAL]
    Update status, priority, or assignee of an existing operational task.
    Requires a cryptographic approval_token from the OpsPilot backend approval boundary.
    """
    call_args = {
        "task_id": task_id,
        "status": status,
        "priority": priority,
        "assignee": assignee,
    }

    if not verify_approval_token("update_operational_task", call_args, approval_token, workspace_id):
        return create_error_envelope(
            system="postgresql",
            tool="update_operational_task",
            error="WRITE_APPROVAL_REQUIRED: Updating task state requires explicit human approval.",
            error_category="APPROVAL_REQUIRED",
            is_write=True
        )

    async with ops_db.session_factory() as session:
        stmt = select(OperationalTask).where(
            OperationalTask.id == task_id,
            OperationalTask.workspace_id == workspace_id
        )
        res = await session.execute(stmt)
        task = res.scalar_one_or_none()
        if not task:
            return create_error_envelope(
                system="postgresql",
                tool="update_operational_task",
                error=f"Task '{task_id}' not found",
                error_category="NOT_FOUND",
                is_write=True
            )

        if status:
            task.status = status
        if priority:
            task.priority = priority
        if assignee:
            task.assignee = assignee
        task.updated_at = utc_now()

        await session.commit()

    return create_success_envelope(
        system="postgresql",
        tool="update_operational_task",
        data={
            "action": "updated_operational_task",
            "task_id": task_id,
            "updated_fields": {k: v for k, v in {"status": status, "priority": priority, "assignee": assignee}.items() if v is not None}
        },
        is_write=True,
        resource_ids_urls=[task_id]
    )

@mcp.tool()
async def update_incident_status(
    incident_id: str,
    status: str,
    approval_token: str = "",
    workspace_id: str = "default-ops"
) -> Dict[str, Any]:
    """
    [WRITE OPERATION - REQUIRES APPROVAL]
    Update status of an operational incident (open, investigating, mitigated, resolved, closed).
    Requires a cryptographic approval_token from the OpsPilot backend approval boundary.
    """
    call_args = {
        "incident_id": incident_id,
        "status": status,
    }

    if not verify_approval_token("update_incident_status", call_args, approval_token, workspace_id):
        return create_error_envelope(
            system="postgresql",
            tool="update_incident_status",
            error="WRITE_APPROVAL_REQUIRED: Incident status updates affect critical operations and require human approval.",
            error_category="APPROVAL_REQUIRED",
            is_write=True
        )

    async with ops_db.session_factory() as session:
        stmt = select(OperationalIncident).where(
            OperationalIncident.id == incident_id,
            OperationalIncident.workspace_id == workspace_id
        )
        res = await session.execute(stmt)
        incident = res.scalar_one_or_none()
        if not incident:
            return create_error_envelope(
                system="postgresql",
                tool="update_incident_status",
                error=f"Incident '{incident_id}' not found",
                error_category="NOT_FOUND",
                is_write=True
            )

        incident.status = status
        incident.updated_at = utc_now()
        await session.commit()

    return create_success_envelope(
        system="postgresql",
        tool="update_incident_status",
        data={
            "action": "updated_incident_status",
            "incident_id": incident_id,
            "new_status": status,
            "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat() + "Z"
        },
        is_write=True,
        resource_ids_urls=[incident_id]
    )

# =========================================================================
# ADDITIONAL READ & DIAGNOSTIC TOOLS (AlgoProfessor Requirements)
# =========================================================================

@mcp.tool()
async def check_database_health(workspace_id: str = "default-ops") -> Dict[str, Any]:
    """
    Check the connectivity, responsiveness, and dialect of the operations database.
    Performs a lightweight query ping and returns latency, dialect, and health status.
    """
    import time
    start = time.perf_counter()
    try:
        from sqlalchemy import text
        async with ops_db.session_factory() as session:
            await session.execute(text("SELECT 1"))
        latency_ms = round((time.perf_counter() - start) * 1000, 2)
        dialect = "postgresql" if "postgresql" in ops_db.db_url else "sqlite"
        return create_success_envelope(
            system="postgresql",
            tool="check_database_health",
            data={
                "status": "connected",
                "healthy": True,
                "dialect": dialect,
                "latency_ms": latency_ms,
                "database_url_configured": bool(ops_db.db_url),
                "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat() + "Z"
            }
        )
    except Exception as ex:
        latency_ms = round((time.perf_counter() - start) * 1000, 2)
        return create_error_envelope(
            system="postgresql",
            tool="check_database_health",
            error=f"Database health check failed: {str(ex)}",
            error_category="CONNECTION_ERROR",
            retryable=True
        )

@mcp.tool()
async def inspect_database_schema(workspace_id: str = "default-ops") -> Dict[str, Any]:
    """
    Inspect the schema of the operations database.
    Returns authorized tables, column definitions, data types, and primary key constraints.
    """
    try:
        from sqlalchemy import inspect
        def _get_schema(conn):
            insp = inspect(conn)
            table_names = insp.get_table_names()
            tables_meta = []
            for t in table_names:
                cols = insp.get_columns(t)
                pk = insp.get_pk_constraint(t)
                pk_cols = pk.get("constrained_columns", []) if pk else []
                tables_meta.append({
                    "table_name": t,
                    "columns": [
                        {
                            "name": c["name"],
                            "type": str(c["type"]),
                            "nullable": c.get("nullable", True),
                            "primary_key": c["name"] in pk_cols
                        }
                        for c in cols
                    ]
                })
            return tables_meta

        async with ops_db.engine.connect() as conn:
            schema_data = await conn.run_sync(_get_schema)

        return create_success_envelope(
            system="postgresql",
            tool="inspect_database_schema",
            data={
                "tables": schema_data,
                "total_tables": len(schema_data),
                "dialect": "postgresql" if "postgresql" in ops_db.db_url else "sqlite"
            },
            resource_ids_urls=[t["table_name"] for t in schema_data]
        )
    except Exception as ex:
        return create_error_envelope(
            system="postgresql",
            tool="inspect_database_schema",
            error=str(ex),
            error_category="SCHEMA_INSPECTION_ERROR",
            retryable=True
        )

import re

FORBIDDEN_SQL_PATTERNS = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|TRUNCATE|GRANT|REVOKE|REPLACE|EXEC|EXECUTE)\b",
    re.IGNORECASE
)

@mcp.tool()
async def execute_read_only_query(query: str, max_rows: int = 50, workspace_id: str = "default-ops") -> Dict[str, Any]:
    """
    Safely execute a validated read-only SQL query against the operations database.
    Enforces strict SELECT-only execution; rejects DDL, DML, and multi-statement queries.
    """
    clean_query = query.strip().rstrip(";").strip()

    if not clean_query:
        return create_error_envelope(
            system="postgresql",
            tool="execute_read_only_query",
            error="Query string cannot be empty",
            error_category="INVALID_QUERY"
        )

    # Strip SQL comments to prevent comment-based evasion
    uncommented = re.sub(r"--.*$", "", clean_query, flags=re.MULTILINE)
    uncommented = re.sub(r"/\*.*?\*/", "", uncommented, flags=re.DOTALL).strip()

    if not uncommented:
        return create_error_envelope(
            system="postgresql",
            tool="execute_read_only_query",
            error="Query contains only comments or whitespace",
            error_category="INVALID_QUERY"
        )

    if ";" in uncommented or ";" in clean_query:
        return create_error_envelope(
            system="postgresql",
            tool="execute_read_only_query",
            error="Multi-statement SQL execution is strictly forbidden for security.",
            error_category="UNAUTHORIZED_SQL"
        )

    match = FORBIDDEN_SQL_PATTERNS.search(uncommented) or FORBIDDEN_SQL_PATTERNS.search(clean_query)
    if match:
        return create_error_envelope(
            system="postgresql",
            tool="execute_read_only_query",
            error=f"Forbidden keyword '{match.group(0).upper()}' detected. Modification queries require cryptographic human approval through designated write tools.",
            error_category="UNAUTHORIZED_SQL"
        )

    if not re.match(r"^(SELECT|WITH)\b", uncommented, re.IGNORECASE):
        return create_error_envelope(
            system="postgresql",
            tool="execute_read_only_query",
            error="Only read-only SELECT or WITH statements are authorized. Modifications require cryptographic approval.",
            error_category="UNAUTHORIZED_SQL"
        )

    limit = min(max(1, max_rows), 100)
    if "LIMIT" not in clean_query.upper():
        clean_query = f"{clean_query} LIMIT {limit}"

    import time
    start = time.perf_counter()
    try:
        from sqlalchemy import text
        async with ops_db.session_factory() as session:
            result = await session.execute(text(clean_query))
            rows = result.mappings().all()
            duration_ms = round((time.perf_counter() - start) * 1000, 2)

            data_rows = []
            for r in rows:
                row_dict = {}
                for k, v in dict(r).items():
                    if isinstance(v, (datetime.datetime, datetime.date)):
                        row_dict[k] = v.isoformat()
                    else:
                        row_dict[k] = v
                data_rows.append(row_dict)

            return create_success_envelope(
                system="postgresql",
                tool="execute_read_only_query",
                data={
                    "query": clean_query,
                    "row_count": len(data_rows),
                    "execution_time_ms": duration_ms,
                    "rows": data_rows
                }
            )
    except Exception as ex:
        return create_error_envelope(
            system="postgresql",
            tool="execute_read_only_query",
            error=f"SQL execution error: {str(ex)}",
            error_category="QUERY_EXECUTION_ERROR",
            retryable=False
        )

if __name__ == "__main__":
    mcp.run()

