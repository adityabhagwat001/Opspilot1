# OpsPilot Automated Testing & Verification Guide

This document details the automated test suite and verification procedures for OpsPilot.

## Test Summary

OpsPilot contains **14 automated integration and security tests** spanning:
1. FastMCP Tool Discovery and Invocation
2. Human-in-the-Loop Security Boundary
3. LangGraph AI Agent Execution and Planning

---

## Test Execution

Run the complete test suite from the repository root:
```powershell
.\.venv\Scripts\pytest.exe -v backend/tests
```

### Expected Output:
```
backend/tests/test_approval_security.py::test_action_hash_deterministic PASSED
backend/tests/test_approval_security.py::test_tampered_parameters_hash_mismatch PASSED
backend/tests/test_approval_security.py::test_forged_approval_token_rejected PASSED
backend/tests/test_approval_security.py::test_genuine_approval_token_verified PASSED
backend/tests/test_approval_security.py::test_approval_lifecycle_and_rejection PASSED
backend/tests/test_langgraph_agent.py::test_langgraph_agent_read_routing PASSED
backend/tests/test_langgraph_agent.py::test_langgraph_agent_write_interrupt_boundary PASSED
backend/tests/test_mcp_servers.py::test_postgres_mcp_tool_discovery PASSED
backend/tests/test_mcp_servers.py::test_postgres_mcp_read_incidents PASSED
backend/tests/test_mcp_servers.py::test_postgres_mcp_write_requires_approval PASSED
backend/tests/test_github_mcp_tool_discovery PASSED
backend/tests/test_github_mcp_write_requires_approval PASSED
backend/tests/test_productivity_mcp_read_messages PASSED
backend/tests/test_productivity_mcp_send_email_requires_approval PASSED
======================= 14 passed in ~2.5s =======================
```

---

## Detailed Test Case Breakdown

### 1. `test_mcp_servers.py`
- `test_postgres_mcp_tool_discovery`: Verifies FastMCP registers all 9 PostgreSQL tools.
- `test_postgres_mcp_read_incidents`: Asserts live retrieval of seeded operational incidents.
- `test_postgres_mcp_write_requires_approval`: Confirms `create_operational_task` cannot be executed without a cryptographic approval token.
- `test_github_mcp_tool_discovery`: Verifies 11 tools exposed on GitHub FastMCP server.
- `test_github_mcp_write_requires_approval`: Confirms `create_issue` is rejected without approval.
- `test_productivity_mcp_read_messages`: Confirms reading messages from the mailbox.
- `test_productivity_mcp_send_email_requires_approval`: Confirms `send_email` rejects unapproved write calls.

### 2. `test_approval_security.py`
- `test_action_hash_deterministic`: Verifies key sorting produces identical hashes regardless of dictionary ordering.
- `test_tampered_parameters_hash_mismatch`: Proves that tampering with parameters (e.g. escalating priority from `p1` to `p0`) changes the hash and invalidates approval.
- `test_forged_approval_token_rejected`: Confirms that arbitrary tokens forged by an attacker or LLM fail HMAC verification.
- `test_genuine_approval_token_verified`: Confirms that backend-signed tokens validate successfully.
- `test_approval_lifecycle_and_rejection`: Proves that rejected requests can never be approved or executed.

### 3. `test_langgraph_agent.py`
- `test_langgraph_agent_read_routing`: Verifies read requests execute tools and return grounded responses.
- `test_langgraph_agent_write_interrupt_boundary`: Verifies write requests halt in the `awaiting_approval` state.
