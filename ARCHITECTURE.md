# OpsPilot System Architecture Specification

## 1. High-Level System Flow

```
[ User Browser ]
       │  (Vite + React 18 + Tailwind SaaS Frontend)
       ▼
[ FastAPI Backend Gateway ] (:8000)
       │
       ├── Authentication & RBAC (JWT, Bcrypt)
       ├── Approval Boundary Service (HMAC-SHA256 Token Generator & Validator)
       ├── Audit Logger (Immutable execution records)
       │
       ▼
[ LangGraph AI Agent Engine ]
       │  (StateGraph with Persistent Execution Checkpointer)
       ├── 1. UNDERSTAND_REQUEST Node (Intent Classification)
       ├── 2. DISCOVER_TOOLS Node (FastMCP tool schema inspection)
       ├── 3. PLAN_ACTIONS Node (Sequential execution strategy)
       ├── 4. EXECUTE_OR_INTERRUPT Node:
       │      ├── Read Tool: Direct execution via FastMCP Router
       │      └── Write Tool: HALT → Persist ApprovalRequest → Await Human
       └── 5. GENERATE_FINAL_RESPONSE Node (Synthesize grounded facts)
              │
              ▼
       [ FastMCP Client Router ]
              │
       ┌──────┼────────────────────────┐
       ▼      ▼                        ▼
[ Postgres FastMCP ]   [ GitHub FastMCP ]     [ Productivity FastMCP ]
  - list_incidents       - list_issues          - list_messages
  - list_tasks           - list_pull_requests   - search_messages
  - create_task [GATE]   - create_issue [GATE]  - send_email [GATE]
  - update_status [GATE] - add_comment [GATE]   - create_event [GATE]
       │                      │                        │
       ▼                      ▼                        ▼
[ PostgreSQL / DB ]    [ GitHub REST API v3 ]  [ Enterprise Mail/Calendar ]
```

---

## 2. FastMCP Integration Architecture

OpsPilot hosts three isolated integration servers running on FastMCP:

### MCP Server 1: PostgreSQL Operations (`mcp_servers/postgres_server/`)
- **Transport**: Standard MCP stdio transport + Async in-process client.
- **Read Operations**: Parameterized SQLAlchemy asynchronous queries over `operational_incidents`, `operational_tasks`, and `system_entities`.
- **Write Operations**: `create_operational_task`, `update_operational_task`, `update_incident_status`.
- **Protection**: Every write handler checks `verify_approval_token`.

### MCP Server 2: GitHub Enterprise (`mcp_servers/github_server/`)
- **Transport**: FastMCP stdio transport + official HTTP REST client (`httpx.AsyncClient`).
- **Read Operations**: `list_repositories`, `get_repository_details`, `list_issues`, `get_issue_details`, `list_pull_requests`, `list_recent_commits`, `get_workflow_runs`.
- **Write Operations**: `create_issue`, `update_issue`, `add_issue_comment`.
- **Verification**: Inspects GitHub API HTTP status code, returns actual issue number and URL upon creation.

### MCP Server 3: Productivity (`mcp_servers/productivity_server/`)
- **Transport**: FastMCP stdio transport.
- **Read Operations**: `list_messages`, `search_messages`, `get_unread_messages`, `check_availability`, `list_events`.
- **Write Operations**: `create_email_draft`, `send_email`, `create_calendar_event`, `cancel_calendar_event`.

---

## 3. Cryptographic Human Approval Protocol

The security boundary works as follows:

1. **Proposal**: When a write tool is proposed, the backend extracts the arguments excluding any tokens:
   $$\text{canonical\_json} = \text{JSON.stringify}(\text{sorted\_arguments})$$
   $$\text{action\_hash} = \text{SHA256}(\text{tool\_name} + ":" + \text{canonical\_json})$$
2. **Approval Request**: An `ApprovalRequest` record is persisted in the database with status `pending`, `action_hash`, and a 15-minute expiration timestamp.
3. **Review**: The human reviewer inspects the exact parameters and hash in the Approval Center.
4. **Execution Token Generation**: Upon human authorization, the trusted backend computes:
   $$\text{signature} = \text{HMAC-SHA256}(\text{APPROVAL\_SECRET}, \text{tool\_name} + ":" + \text{timestamp} + ":" + \text{action\_hash})$$
   $$\text{approval\_token} = \text{timestamp} + "." + \text{action\_hash} + "." + \text{signature}$$
5. **Tool Execution**: The tool is invoked with `approval_token`. The FastMCP server verifies the HMAC signature. If valid, the write is executed. If invalid or tampered, the tool immediately rejects the call.
6. **Audit Trail**: Every execution result is logged to `audit_logs` with the approver's user ID.
