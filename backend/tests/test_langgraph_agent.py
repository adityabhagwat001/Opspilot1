"""
LangGraph AI Agent Execution and Planning Tests
"""

import pytest
from app.agents.agent_graph import agent_executor

@pytest.mark.asyncio
async def test_langgraph_agent_read_routing():
    state = {
        "execution_id": "test-read-01",
        "user_id": "usr-admin-01",
        "workspace_id": "default-ops",
        "user_request": "Show me all open operational incidents from the database.",
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
    result = await agent_executor.ainvoke(state)
    assert result["execution_status"] == "completed"
    assert result["pending_approval"] is None
    assert len(result["tool_results"]) >= 1
    assert "Live Operational Findings" in result["final_response"]

@pytest.mark.asyncio
async def test_langgraph_agent_write_interrupt_boundary():
    state = {
        "execution_id": "test-write-01",
        "user_id": "usr-admin-01",
        "workspace_id": "default-ops",
        "user_request": "Create a GitHub issue for fixing the authentication timeout.",
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
    result = await agent_executor.ainvoke(state)
    assert result["execution_status"] == "awaiting_approval"
    assert result["pending_approval"] is not None
    assert result["pending_approval"]["tool_name"] == "create_issue"
    assert result["pending_approval"]["target_system"] == "github"
    assert "Action Proposal — Human Approval Required" in result["final_response"]
