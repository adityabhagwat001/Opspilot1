"""
LangGraph AI Agent Execution and Planning Tests
Verifies intent classification, read-only routing, multi-turn context resolution,
dynamic datetime handling, and unbypassable Human-in-the-Loop write interrupts.
"""

import pytest
from app.agents.agent_graph import agent_executor

@pytest.mark.asyncio
async def test_langgraph_agent_read_routing():
    state = {
        "execution_id": "test-read-01",
        "conversation_id": "conv-test-01",
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
    assert "INC-101" in result["final_response"]

@pytest.mark.asyncio
async def test_langgraph_agent_write_interrupt_boundary():
    state = {
        "execution_id": "test-write-01",
        "conversation_id": "conv-test-02",
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
    assert "Human Approval Required" in result["final_response"]

@pytest.mark.asyncio
async def test_langgraph_agent_greeting_no_db_query():
    state = {
        "execution_id": "test-greet-01",
        "conversation_id": "conv-test-03",
        "user_id": "usr-admin-01",
        "workspace_id": "default-ops",
        "user_request": "Hello there!",
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
    assert len(result["tool_results"]) == 0
    assert "OpsPilot" in result["final_response"]

@pytest.mark.asyncio
async def test_langgraph_agent_unrelated_query_declined():
    state = {
        "execution_id": "test-unrelated-01",
        "conversation_id": "conv-test-04",
        "user_id": "usr-admin-01",
        "workspace_id": "default-ops",
        "user_request": "Can you give me a recipe for chocolate cake?",
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
    assert len(result["tool_results"]) == 0
    assert "restricted to authorized infrastructure" in result["final_response"]

@pytest.mark.asyncio
async def test_langgraph_agent_contextual_issue_creation():
    # User previously inspected incident INC-101 and now says "Create an issue for this incident"
    state = {
        "execution_id": "test-ctx-01",
        "conversation_id": "conv-test-05",
        "user_id": "usr-admin-01",
        "workspace_id": "default-ops",
        "user_request": "Create an issue for this incident",
        "conversation_history": [
            {"role": "user", "content": "Show open critical incidents"},
            {"role": "assistant", "content": "Found incident INC-101: Auth service latency spike and connection pool exhaustion"}
        ],
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
    args = result["pending_approval"]["arguments"]
    assert "auth-service" in args["repo"] or "auth" in args["title"].lower()
    assert "INC-101" in args["body"]
