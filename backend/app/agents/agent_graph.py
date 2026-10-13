"""
OpsPilot Enterprise Stateful LangGraph Agent
Implements multi-step planning, tool discovery, fact grounding, and Human-in-the-Loop write interrupts.
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional, TypedDict, Annotated
from langgraph.graph import StateGraph, END
from app.integrations.mcp_router import mcp_router, WRITE_TOOLS
from app.core.config import settings

logger = logging.getLogger("opspilot.agent")

class OpsAgentState(TypedDict):
    execution_id: str
    user_id: str
    workspace_id: str
    user_request: str
    conversation_history: List[Dict[str, str]]
    target_systems: List[str]
    available_tools: List[Dict[str, Any]]
    planned_actions: List[Dict[str, Any]]
    completed_actions: List[Dict[str, Any]]
    pending_approval: Optional[Dict[str, Any]]
    tool_results: List[Dict[str, Any]]
    final_response: Optional[str]
    execution_status: str
    current_step: str
    errors: List[str]

# =========================================================================
# GRAPH NODES
# =========================================================================

async def understand_request_node(state: OpsAgentState) -> Dict[str, Any]:
    """
    Analyzes user request to identify required enterprise systems and intent.
    """
    req = state["user_request"].lower()
    systems = []
    
    # Systems identification
    if any(k in req for k in ["incident", "database", "task", "operational", "record", "db"]):
        systems.append("postgresql")
    if any(k in req for k in ["github", "issue", "repo", "repository", "pull request", "pr", "commit"]):
        systems.append("github")
    if any(k in req for k in ["email", "mail", "unread", "inbox", "message"]):
        systems.append("email")
    if any(k in req for k in ["calendar", "meeting", "schedule", "availability", "slot", "tomorrow"]):
        systems.append("calendar")
    
    # Multi-system fallback
    if not systems:
        systems = ["postgresql", "github", "email", "calendar"]

    return {
        "target_systems": systems,
        "current_step": "Understood request intent",
        "execution_status": "analyzing"
    }

async def discover_tools_node(state: OpsAgentState) -> Dict[str, Any]:
    """
    Discovers available MCP tools matching identified target systems.
    """
    all_tools = await mcp_router.list_all_tools()
    matched = [t for t in all_tools if t["system"] in state["target_systems"] or not state["target_systems"]]
    
    return {
        "available_tools": matched,
        "current_step": f"Discovered {len(matched)} MCP tools across systems: {', '.join(state['target_systems'])}",
        "execution_status": "tools_discovered"
    }

async def plan_actions_node(state: OpsAgentState) -> Dict[str, Any]:
    """
    Plans sequential tool calls. Distinguishes read actions from write actions.
    """
    req = state["user_request"].lower()
    planned = []
    
    # Scenario A / DB Read:
    if "incident" in req and any(k in req for k in ["show", "list", "check", "get", "what", "find"]):
        planned.append({"tool": "list_incidents", "system": "postgresql", "args": {}, "is_write": False})
    elif "database" in req or "summary" in req or "health" in req:
        planned.append({"tool": "get_operations_summary", "system": "postgresql", "args": {}, "is_write": False})

    # DB Write Task:
    if "create" in req and ("task" in req or "remediation" in req):
        # Extract title
        title = "Investigate operational latency"
        if "for" in req:
            title = req.split("for", 1)[1].strip().capitalize()
        planned.append({
            "tool": "create_operational_task",
            "system": "postgresql",
            "args": {"title": title, "description": f"Created via OpsPilot for: {state['user_request']}", "priority": "p1"},
            "is_write": True,
            "summary": f"Create operational task: '{title}'"
        })

    # Scenario B: GitHub Issue List
    if ("github" in req or "issue" in req or "repo" in req) and any(k in req for k in ["list", "check", "show", "open", "find"]):
        owner = settings.GITHUB_DEFAULT_OWNER or "enterprise-org"
        repo = settings.GITHUB_DEFAULT_REPO or "core-platform"
        planned.append({
            "tool": "list_issues",
            "system": "github",
            "args": {"owner": owner, "repo": repo, "state": "open"},
            "is_write": False
        })

    # Scenario C: GitHub Write (Issue Creation)
    if "create" in req and "issue" in req:
        owner = settings.GITHUB_DEFAULT_OWNER or "enterprise-org"
        repo = settings.GITHUB_DEFAULT_REPO or "core-platform"
        title = "Fix authentication timeout in auth-service"
        if "for" in req:
            title = req.split("for", 1)[1].strip().capitalize()
        planned.append({
            "tool": "create_issue",
            "system": "github",
            "args": {
                "owner": owner,
                "repo": repo,
                "title": title,
                "body": f"Automated ticket created via OpsPilot AI Operations Assistant.\nUser Request: {state['user_request']}\nTarget: auth-service connection pool stability."
            },
            "is_write": True,
            "summary": f"Create GitHub issue '{title}' in repository '{owner}/{repo}'"
        })

    # Scenario D: Email Read
    if "email" in req or "mail" in req or "unread" in req or "message" in req:
        if any(k in req for k in ["unread", "important", "deployment", "find", "check", "show"]):
            planned.append({"tool": "get_unread_messages", "system": "email", "args": {"max_results": 5}, "is_write": False})

    # Scenario E: Email Draft / Send
    if "send" in req and "email" in req:
        recipient = "engineering-team@enterprise.internal"
        subject = "Operational Update: Deployment Status & Action Plan"
        body = f"Team,\n\nPlease note the following update regarding current operations:\n{state['user_request']}\n\nRegards,\nOpsPilot Operations Assistant"
        planned.append({
            "tool": "send_email",
            "system": "email",
            "args": {"recipient": recipient, "subject": subject, "body": body},
            "is_write": True,
            "summary": f"Send external email to '{recipient}' with subject '{subject}'"
        })
    elif "draft" in req and "email" in req:
        recipient = "engineering-team@enterprise.internal"
        subject = "Draft: Deployment Delay & Canary Rollback"
        body = f"Team,\n\nDeployment delay notice regarding current deployment status.\n{state['user_request']}"
        planned.append({
            "tool": "create_email_draft",
            "system": "email",
            "args": {"recipient": recipient, "subject": subject, "body": body},
            "is_write": True,
            "summary": f"Create mailbox draft to '{recipient}' with subject '{subject}'"
        })

    # Scenario F: Calendar Scheduling
    if "schedule" in req or "meeting" in req or "calendar" in req:
        if "check" in req or "availability" in req:
            planned.append({
                "tool": "check_availability",
                "system": "calendar",
                "args": {"start_time": "2026-10-14T15:00:00", "end_time": "2026-10-14T16:00:00"},
                "is_write": False
            })
        elif "schedule" in req or "create" in req:
            planned.append({
                "tool": "create_calendar_event",
                "system": "calendar",
                "args": {
                    "title": "Development Team Operations Alignment",
                    "start_time": "2026-10-14T15:00:00",
                    "end_time": "2026-10-14T16:00:00",
                    "attendees": ["dev-team@enterprise.internal", "oncall@enterprise.internal"],
                    "description": f"Scheduled meeting for: {state['user_request']}"
                },
                "is_write": True,
                "summary": "Schedule meeting 'Development Team Operations Alignment' for tomorrow at 3 PM (UTC)"
            })

    # Default operations summary if nothing planned
    if not planned:
        planned.append({"tool": "get_operations_summary", "system": "postgresql", "args": {}, "is_write": False})

    return {
        "planned_actions": planned,
        "current_step": f"Planned {len(planned)} operational action(s)",
        "execution_status": "planned"
    }

async def execute_or_interrupt_node(state: OpsAgentState) -> Dict[str, Any]:
    """
    Executes read-only tools immediately.
    Halts immediately upon encountering any write tool, producing pending approval state.
    """
    results = list(state.get("tool_results") or [])
    completed = list(state.get("completed_actions") or [])
    pending_approval = None
    
    for action in state.get("planned_actions", []):
        tool_name = action["tool"]
        is_write = action.get("is_write", False) or mcp_router.is_write_tool(tool_name)
        
        if is_write:
            # STOP! Human Approval Boundary reached
            pending_approval = {
                "target_system": action.get("system", mcp_router.get_target_system(tool_name)),
                "tool_name": tool_name,
                "arguments": action.get("args", {}),
                "action_summary": action.get("summary", f"Proposed execution of write tool '{tool_name}'"),
                "status": "pending_human_approval"
            }
            # Break immediately, do NOT execute write
            break
        else:
            # Read tool - execute through MCP Router
            res = await mcp_router.execute_tool(tool_name, action.get("args", {}))
            results.append({"tool": tool_name, "result": res})
            completed.append(action)

    status = "awaiting_approval" if pending_approval else "executed_read_tools"
    return {
        "tool_results": results,
        "completed_actions": completed,
        "pending_approval": pending_approval,
        "execution_status": status,
        "current_step": "Awaiting human approval for write action" if pending_approval else "Read operations completed successfully"
    }

async def generate_response_node(state: OpsAgentState) -> Dict[str, Any]:
    """
    Synthesizes facts retrieved from live MCP tools into a clear, grounded response.
    Never invents records or claims a proposed write has already executed.
    """
    tool_results = state.get("tool_results", [])
    pending = state.get("pending_approval")
    
    lines = []
    
    # 1. Grounded Factual Findings
    if tool_results:
        lines.append("### Live Operational Findings (Retrieved via MCP):")
        for tr in tool_results:
            tool = tr["tool"]
            res = tr["result"]
            
            if tool == "list_incidents":
                if isinstance(res, list):
                    lines.append(f"\n**Open Operational Incidents ({len(res)} found in PostgreSQL):**")
                    for inc in res:
                        lines.append(f"- **[{inc.get('id')}]** `{inc.get('severity').upper()}` - **{inc.get('title')}** (Status: *{inc.get('status')}*, Service: `{inc.get('service')}`)")
            elif tool == "get_operations_summary":
                lines.append("\n**System Operations Overview:**")
                lines.append(f"- Total Incidents: {res.get('total_incidents', 0)} ({res.get('critical_incidents', 0)} Critical)")
                lines.append(f"- Active Remediation Tasks: {res.get('active_tasks', 0)}")
                lines.append(f"- Platform Health: `{res.get('system_status', 'healthy').upper()}`")
            elif tool == "list_issues":
                count = res.get("count", 0)
                issues = res.get("issues", [])
                lines.append(f"\n**GitHub Issues ({count} retrieved):**")
                for iss in issues[:5]:
                    lines.append(f"- Issue #{iss.get('number')}: **{iss.get('title')}** (Labels: {', '.join(iss.get('labels', [])) or 'None'})")
            elif tool == "get_unread_messages":
                msgs = res.get("messages", [])
                lines.append(f"\n**Unread Operational Emails ({len(msgs)} retrieved):**")
                for m in msgs:
                    lines.append(f"- **From:** `{m.get('sender')}` | **Subject:** {m.get('subject')}")
                    lines.append(f"  *Preview:* {m.get('snippet')}")
            elif tool == "check_availability":
                lines.append("\n**Calendar Availability Check:**")
                lines.append(f"- Slot Available: **{res.get('is_available')}** (Conflicts: {res.get('conflict_count')})")
            else:
                lines.append(f"\n**Tool `{tool}` Output:**\n```json\n{json.dumps(res, indent=2)}\n```")

    # 2. Human Approval Boundary Notification
    if pending:
        lines.append("\n---")
        lines.append("### Action Proposal — Human Approval Required")
        lines.append(f"> **Target System:** `{pending['target_system'].upper()}`")
        lines.append(f"> **Tool:** `{pending['tool_name']}`")
        lines.append(f"> **Proposed Action:** {pending['action_summary']}")
        lines.append("\n**Proposed Parameters:**")
        lines.append(f"```json\n{json.dumps(pending['arguments'], indent=2)}\n```")
        lines.append("\n*Safety Enforcement: This write operation has NOT been executed. Review and approve in the Approval Center to apply changes.*")

    final_text = "\n".join(lines) if lines else "No operational records found matching your query."
    
    return {
        "final_response": final_text,
        "execution_status": "completed" if not pending else "awaiting_approval",
        "current_step": "Final response generated"
    }

# Build LangGraph Workflow
def build_agent_graph():
    workflow = StateGraph(OpsAgentState)
    
    workflow.add_node("understand_request", understand_request_node)
    workflow.add_node("discover_tools", discover_tools_node)
    workflow.add_node("plan_actions", plan_actions_node)
    workflow.add_node("execute_or_interrupt", execute_or_interrupt_node)
    workflow.add_node("generate_response", generate_response_node)

    workflow.set_entry_point("understand_request")
    workflow.add_edge("understand_request", "discover_tools")
    workflow.add_edge("discover_tools", "plan_actions")
    workflow.add_edge("plan_actions", "execute_or_interrupt")
    workflow.add_edge("execute_or_interrupt", "generate_response")
    workflow.add_edge("generate_response", END)

    return workflow.compile()

agent_executor = build_agent_graph()
