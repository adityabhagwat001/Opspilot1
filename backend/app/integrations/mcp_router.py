"""
OpsPilot MCP Client & Tool Router
Bridges the LangGraph AI Agent to custom FastMCP Servers (PostgreSQL, GitHub, Productivity).
Classifies tools into Read vs Protected Write, provides schema definitions, and invokes tools.
"""

import os
import sys
import json
import logging
from typing import Dict, Any, List, Optional

# Add project root to path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from mcp_servers.postgres_server.server import mcp as pg_mcp
from mcp_servers.github_server.server import mcp as gh_mcp
from mcp_servers.productivity_server.server import mcp as prod_mcp

logger = logging.getLogger("opspilot.mcp_router")

# Tool category mapping
WRITE_TOOLS = {
    # Postgres
    "create_operational_task": "postgresql",
    "update_operational_task": "postgresql",
    "update_incident_status": "postgresql",
    # GitHub
    "create_issue": "github",
    "update_issue": "github",
    "add_issue_comment": "github",
    "create_branch": "github",
    "commit_file_changes": "github",
    "create_pull_request": "github",
    "rerun_workflow": "github",
    # Productivity (Email & Calendar)
    "create_email_draft": "email",
    "send_email": "email",
    "create_calendar_event": "calendar",
    "update_calendar_event": "calendar",
    "cancel_calendar_event": "calendar",
}

SERVER_MAPPING = {
    # Postgres Server
    "list_database_entities": pg_mcp,
    "get_operations_summary": pg_mcp,
    "list_incidents": pg_mcp,
    "get_incident_details": pg_mcp,
    "list_operational_tasks": pg_mcp,
    "get_task_details": pg_mcp,
    "create_operational_task": pg_mcp,
    "update_operational_task": pg_mcp,
    "update_incident_status": pg_mcp,

    # GitHub Server
    "get_authenticated_user": gh_mcp,
    "list_repositories": gh_mcp,
    "get_repository_details": gh_mcp,
    "get_repository_file": gh_mcp,
    "list_issues": gh_mcp,
    "get_issue_details": gh_mcp,
    "list_pull_requests": gh_mcp,
    "get_pull_request_details": gh_mcp,
    "get_pull_request_diff": gh_mcp,
    "list_commits": gh_mcp,
    "list_recent_commits": gh_mcp,
    "list_workflow_runs": gh_mcp,
    "get_workflow_runs": gh_mcp,
    "list_workflow_run_jobs": gh_mcp,
    "get_workflow_logs": gh_mcp,
    "create_issue": gh_mcp,
    "update_issue": gh_mcp,
    "add_issue_comment": gh_mcp,
    "create_branch": gh_mcp,
    "commit_file_changes": gh_mcp,
    "create_pull_request": gh_mcp,
    "rerun_workflow": gh_mcp,

    # Productivity Server
    "list_messages": prod_mcp,
    "search_messages": prod_mcp,
    "get_message": prod_mcp,
    "get_unread_messages": prod_mcp,
    "create_email_draft": prod_mcp,
    "send_email": prod_mcp,
    "list_calendars": prod_mcp,
    "list_events": prod_mcp,
    "get_event": prod_mcp,
    "check_availability": prod_mcp,
    "create_calendar_event": prod_mcp,
    "update_calendar_event": prod_mcp,
    "cancel_calendar_event": prod_mcp,
}

class MCPToolRouter:
    def __init__(self):
        self.servers = {
            "postgresql": pg_mcp,
            "github": gh_mcp,
            "productivity": prod_mcp,
        }

    async def list_all_tools(self) -> List[Dict[str, Any]]:
        """
        Discovers tools across all custom FastMCP servers with parameter schemas.
        """
        all_tools = []
        for system_name, server in self.servers.items():
            tools = await server.list_tools()
            for t in tools:
                is_write = t.name in WRITE_TOOLS
                all_tools.append({
                    "name": t.name,
                    "description": t.description or "",
                    "system": WRITE_TOOLS.get(t.name, system_name),
                    "is_write": is_write,
                    "requires_approval": is_write,
                    "parameters": getattr(t, "parameters", None) or getattr(t, "args_schema", {})
                })
        return all_tools

    def is_write_tool(self, tool_name: str) -> bool:
        return tool_name in WRITE_TOOLS

    def get_target_system(self, tool_name: str) -> str:
        if tool_name in WRITE_TOOLS:
            return WRITE_TOOLS[tool_name]
        if tool_name in SERVER_MAPPING:
            m = SERVER_MAPPING[tool_name]
            if m == pg_mcp: return "postgresql"
            if m == gh_mcp: return "github"
            if any(k in tool_name for k in ["message", "mail"]): return "email"
            if any(k in tool_name for k in ["calendar", "event", "availability"]): return "calendar"
            return "productivity"
        return "unknown"

    async def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Invokes an authorized tool via FastMCP.
        If write tool and approval_token is missing, returns structured APPROVAL_REQUIRED payload.
        """
        actual_tool = tool_name
        actual_args = dict(arguments or {})
        if tool_name == "list_workflow_runs":
            actual_tool = "get_workflow_runs"
            actual_args.pop("status", None)
        elif tool_name == "list_commits":
            actual_tool = "list_recent_commits"

        server = SERVER_MAPPING.get(actual_tool)
        if not server:
            return {"error": f"Tool '{tool_name}' not recognized by any MCP server."}

        try:
            # Call tool on FastMCP instance
            result = await server.call_tool(actual_tool, actual_args)
            
            # FastMCP call_tool returns result or Content list
            if hasattr(result, "content"):
                # Handle standard MCP ToolResult
                contents = []
                for c in result.content:
                    if hasattr(c, "text"):
                        try:
                            contents.append(json.loads(c.text))
                        except Exception:
                            contents.append(c.text)
                if len(contents) == 1:
                    return contents[0] if isinstance(contents[0], dict) else {"result": contents[0]}
                return {"results": contents}
            
            if isinstance(result, (dict, list)):
                return result
            return {"result": str(result)}
        except Exception as ex:
            logger.error(f"Error executing MCP tool '{tool_name}': {ex}", exc_info=True)
            return {"error": str(ex), "status": "FAILED", "tool_name": tool_name}

mcp_router = MCPToolRouter()
