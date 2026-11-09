"""
OpsPilot Phase 7: PostgreSQL MCP Schema Introspection & Safe Read-Only SQL Test Suite
Verifies:
- Dynamic schema introspection: Table names, column definitions, data types, and primary key constraints
- Safe read-only SQL execution: SELECT and WITH statements execute with row limit enforcement
- Security boundaries: Strict rejection of DDL/DML keywords (INSERT, UPDATE, DELETE, DROP, ALTER, TRUNCATE)
- Multi-statement injection prevention: Semicolon splitting strictly blocked
- Comment-based evasion prevention: SQL comment masking blocked
- Operations database health check ping & dialect telemetry
- LangGraph agent integration for schema inspection and natural-language query routing
"""

import pytest
from app.integrations.mcp_router import mcp_router
from app.agents.agent_graph import agent_executor
from app.core.db import init_system_db

@pytest.mark.asyncio
async def test_inspect_database_schema_tool():
    """Verify inspect_database_schema discovers tables, columns, data types, and primary keys."""
    res = await mcp_router.execute_tool("inspect_database_schema", {"workspace_id": "default-ops"})
    assert res.get("success") is True or res.get("status") == "SUCCESS"
    data = res.get("data", {})
    tables = data.get("tables", [])
    assert len(tables) > 0

    table_names = [t["table_name"] for t in tables]
    # Check that operational tables exist in schema
    assert any("operational_incidents" in t for t in table_names)
    assert any("operational_tasks" in t for t in table_names)

    # Inspect column structures for operational_incidents
    inc_table = next(t for t in tables if "operational_incidents" in t["table_name"])
    col_names = [c["name"] for c in inc_table["columns"]]
    assert "id" in col_names
    assert "title" in col_names
    assert "severity" in col_names
    assert "status" in col_names

    # Verify primary key identification
    id_col = next(c for c in inc_table["columns"] if c["name"] == "id")
    assert id_col["primary_key"] is True

@pytest.mark.asyncio
async def test_execute_read_only_query_valid_select():
    """Verify safe SELECT queries execute and return structured rows with execution time."""
    query = "SELECT id, title, severity, status FROM operational_incidents WHERE status = 'open'"
    res = await mcp_router.execute_tool("execute_read_only_query", {"query": query, "max_rows": 5})
    assert res.get("success") is True or res.get("status") == "SUCCESS"
    data = res.get("data", {})
    assert "rows" in data
    assert "execution_time_ms" in data
    assert isinstance(data["rows"], list)

@pytest.mark.asyncio
async def test_execute_read_only_query_valid_with_cte():
    """Verify Common Table Expressions (WITH queries) are authorized for complex analytics."""
    query = "WITH active_incidents AS (SELECT id, title, severity FROM operational_incidents) SELECT * FROM active_incidents"
    res = await mcp_router.execute_tool("execute_read_only_query", {"query": query, "max_rows": 3})
    assert res.get("success") is True or res.get("status") == "SUCCESS"
    data = res.get("data", {})
    assert "rows" in data

@pytest.mark.asyncio
async def test_execute_read_only_query_blocks_destructive_dml():
    """Verify INSERT, UPDATE, DELETE queries are blocked with UNAUTHORIZED_SQL."""
    # 1. INSERT blocked
    insert_res = await mcp_router.execute_tool("execute_read_only_query", {
        "query": "INSERT INTO operational_tasks (title) VALUES ('Malicious Task')"
    })
    assert insert_res.get("success") is False or insert_res.get("status") in ("FAILED", "ERROR")
    assert "INSERT" in (insert_res.get("error") or "")

    # 2. UPDATE blocked
    update_res = await mcp_router.execute_tool("execute_read_only_query", {
        "query": "UPDATE operational_incidents SET status = 'closed'"
    })
    assert update_res.get("success") is False or update_res.get("status") in ("FAILED", "ERROR")
    assert "UPDATE" in (update_res.get("error") or "")

    # 3. DELETE blocked
    delete_res = await mcp_router.execute_tool("execute_read_only_query", {
        "query": "DELETE FROM operational_tasks"
    })
    assert delete_res.get("success") is False or delete_res.get("status") in ("FAILED", "ERROR")
    assert "DELETE" in (delete_res.get("error") or "")

@pytest.mark.asyncio
async def test_execute_read_only_query_blocks_ddl_and_destructive_commands():
    """Verify DROP, ALTER, TRUNCATE, and schema alteration keywords are blocked."""
    # 1. DROP blocked
    drop_res = await mcp_router.execute_tool("execute_read_only_query", {
        "query": "DROP TABLE operational_tasks"
    })
    assert drop_res.get("success") is False or drop_res.get("status") in ("FAILED", "ERROR")
    assert "DROP" in (drop_res.get("error") or "")

    # 2. ALTER blocked
    alter_res = await mcp_router.execute_tool("execute_read_only_query", {
        "query": "ALTER TABLE operational_tasks ADD COLUMN rogue text"
    })
    assert alter_res.get("success") is False or alter_res.get("status") in ("FAILED", "ERROR")
    assert "ALTER" in (alter_res.get("error") or "")

    # 3. TRUNCATE blocked
    trunc_res = await mcp_router.execute_tool("execute_read_only_query", {
        "query": "TRUNCATE operational_incidents"
    })
    assert trunc_res.get("success") is False or trunc_res.get("status") in ("FAILED", "ERROR")
    assert "TRUNCATE" in (trunc_res.get("error") or "")

@pytest.mark.asyncio
async def test_execute_read_only_query_blocks_multistatement_injection():
    """Verify semicolon chaining and multi-statement SQL attacks are blocked."""
    chained_res = await mcp_router.execute_tool("execute_read_only_query", {
        "query": "SELECT 1; DROP TABLE operational_incidents"
    })
    assert chained_res.get("success") is False or chained_res.get("status") in ("FAILED", "ERROR")
    assert "Multi-statement" in (chained_res.get("error") or "")

@pytest.mark.asyncio
async def test_execute_read_only_query_blocks_comment_evasion():
    """Verify comment-based evasion (-- and /* */) cannot bypass destructive command blocking."""
    # Line comment masking
    comment_res = await mcp_router.execute_tool("execute_read_only_query", {
        "query": "-- comment\nDROP TABLE operational_incidents"
    })
    assert comment_res.get("success") is False or comment_res.get("status") in ("FAILED", "ERROR")

    # Block comment masking
    block_res = await mcp_router.execute_tool("execute_read_only_query", {
        "query": "/* safe comment */ DELETE FROM operational_tasks"
    })
    assert block_res.get("success") is False or block_res.get("status") in ("FAILED", "ERROR")

@pytest.mark.asyncio
async def test_database_health_check_tool():
    """Verify check_database_health returns latency, dialect, and healthy status."""
    res = await mcp_router.execute_tool("check_database_health", {"workspace_id": "default-ops"})
    assert res.get("success") is True or res.get("status") == "SUCCESS"
    data = res.get("data", {})
    assert data.get("healthy") is True
    assert data.get("dialect") in ("postgresql", "sqlite")
    assert data.get("latency_ms", -1) >= 0

@pytest.mark.asyncio
async def test_langgraph_agent_schema_and_query_intents():
    """Verify LangGraph agent plans and executes inspect_database_schema and execute_read_only_query."""
    await init_system_db()

    # 1. Natural language schema inquiry
    state1 = {
        "execution_id": "test-schema-01",
        "conversation_id": "conv-schema-test",
        "user_id": "usr-operator-01",
        "workspace_id": "default-ops",
        "user_request": "Inspect the database schema and show me all tables",
        "conversation_history": [],
        "target_systems": [],
        "available_tools": [],
        "planned_actions": [],
        "completed_actions": [],
        "pending_approval": None,
        "tool_results": [],
        "final_response": None,
        "execution_status": "received",
        "current_step": "init",
        "errors": []
    }
    schema_state = await agent_executor.ainvoke(state1)
    assert schema_state["execution_status"] in ("completed", "executed_read_tools")
    assert any(a["tool"] == "inspect_database_schema" for a in schema_state["completed_actions"])
    assert "operational_incidents" in schema_state["final_response"] or "Database Schema" in schema_state["final_response"]

    # 2. Natural language read query inquiry
    state2 = {
        "execution_id": "test-query-01",
        "conversation_id": "conv-query-test",
        "user_id": "usr-operator-01",
        "workspace_id": "default-ops",
        "user_request": "Show me the latest records in my database",
        "conversation_history": [],
        "target_systems": [],
        "available_tools": [],
        "planned_actions": [],
        "completed_actions": [],
        "pending_approval": None,
        "tool_results": [],
        "final_response": None,
        "execution_status": "received",
        "current_step": "init",
        "errors": []
    }
    query_state = await agent_executor.ainvoke(state2)
    assert query_state["execution_status"] in ("completed", "executed_read_tools")
    assert any(a["tool"] in ("execute_read_only_query", "list_incidents") for a in query_state["completed_actions"])
    assert len(query_state["final_response"]) > 0
