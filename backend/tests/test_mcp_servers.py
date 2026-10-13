"""
Automated Unit and Integration Tests for OpsPilot Custom FastMCP Servers
Tests tool discovery, typed response envelopes, schema validation, and write boundary rejection.
"""

import pytest
import asyncio
from mcp_servers.postgres_server.server import (
    mcp as pg_mcp,
    list_incidents,
    get_incident_details,
    create_operational_task,
    get_operations_summary
)
from mcp_servers.github_server.server import (
    mcp as gh_mcp,
    list_issues,
    create_issue
)
from mcp_servers.productivity_server.server import (
    mcp as prod_mcp,
    list_messages,
    check_availability,
    send_email
)

@pytest.mark.asyncio
async def test_postgres_mcp_tool_discovery():
    tools = await pg_mcp.list_tools()
    tool_names = [t.name for t in tools]
    assert "list_incidents" in tool_names
    assert "get_operations_summary" in tool_names
    assert "create_operational_task" in tool_names
    assert len(tools) >= 9

@pytest.mark.asyncio
async def test_postgres_mcp_read_incidents():
    envelope = await list_incidents()
    assert envelope["success"] is True
    assert envelope["system"] == "postgresql"
    assert envelope["is_write"] is False
    incidents = envelope["data"]
    assert isinstance(incidents, list)
    assert len(incidents) >= 1
    first = incidents[0]
    assert "id" in first
    assert "title" in first
    assert "severity" in first

@pytest.mark.asyncio
async def test_postgres_mcp_write_requires_approval():
    # Attempt write without approval token
    res = await create_operational_task(
        title="Unauthorized Task",
        description="Should be rejected by FastMCP approval gate"
    )
    assert res["success"] is False
    assert res["is_write"] is True
    assert res.get("error_category") == "APPROVAL_REQUIRED" or res.get("status") == "APPROVAL_REQUIRED"
    assert "WRITE_APPROVAL_REQUIRED" in res.get("error", "")

@pytest.mark.asyncio
async def test_github_mcp_tool_discovery():
    tools = await gh_mcp.list_tools()
    tool_names = [t.name for t in tools]
    assert "list_issues" in tool_names
    assert "create_issue" in tool_names
    assert len(tools) >= 11

@pytest.mark.asyncio
async def test_github_mcp_write_requires_approval():
    res = await create_issue(
        owner="enterprise-org",
        repo="core-platform",
        title="Unapproved Issue",
        body="Must fail without cryptographic token"
    )
    assert res["success"] is False
    assert res["is_write"] is True
    assert res.get("error_category") == "APPROVAL_REQUIRED" or res.get("status") == "APPROVAL_REQUIRED"
    assert "WRITE_APPROVAL_REQUIRED" in res.get("error", "")

@pytest.mark.asyncio
async def test_productivity_mcp_read_messages():
    envelope = await list_messages(max_results=5)
    assert envelope["success"] is True
    assert envelope["system"] == "email"
    assert "messages" in envelope["data"]
    assert len(envelope["data"]["messages"]) >= 1

@pytest.mark.asyncio
async def test_productivity_mcp_send_email_requires_approval():
    res = await send_email(
        recipient="exec@enterprise.internal",
        subject="Unapproved Notice",
        body="Must be blocked"
    )
    assert res["success"] is False
    assert res["is_write"] is True
    assert res.get("error_category") == "APPROVAL_REQUIRED" or res.get("status") == "APPROVAL_REQUIRED"
    assert "WRITE_APPROVAL_REQUIRED" in res.get("error", "")
