# OpsPilot — Enterprise Agentic AI Platform

> **Live Company Integrations via FastMCP • PostgreSQL • GitHub API • LangGraph • Mandatory Human Write Approval Boundary**

OpsPilot is a centralized enterprise AI operations assistant engineered for Agentic AI Engineers and Solutions Architects. It connects to live company systems (PostgreSQL operational databases, GitHub repositories, company email, and calendars) through custom **Model Context Protocol (MCP)** servers built on **FastMCP**.

---

## Key Architectural Principles

1. **Acts on Live Systems via Custom FastMCP Servers**:
   OpsPilot does not simply call arbitrary external scripts; it discovers and invokes tools strictly across three custom FastMCP integration servers:
   - **PostgreSQL FastMCP Server** (`mcp_servers/postgres_server/`): Live operational incidents, tasks, entities, and status machines.
   - **GitHub FastMCP Server** (`mcp_servers/github_server/`): Issues, pull requests, commits, and workflow runs via official GitHub REST API v3.
   - **Productivity FastMCP Server** (`mcp_servers/productivity_server/`): Mailbox search, unread query, email drafting/sending, and calendar conflict detection/scheduling.

2. **Mandatory Human-in-the-Loop Write Approval Boundary**:
   **The AI model NEVER receives authority to write to external systems directly.**
   - When a write action is proposed (`create_issue`, `send_email`, `create_calendar_event`, `create_operational_task`), the backend halts execution.
   - A cryptographic action hash (`SHA-256`) is computed from canonical arguments.
   - An approval ticket is persisted with a 15-minute expiration window.
   - A human reviewer reviews the exact proposed action in the **Approval Center**.
   - Upon approval, the backend issues an unforgeable, HMAC-signed approval token (`timestamp.action_hash.signature`).
   - The FastMCP server verifies the signature before executing the tool.
   - If rejected, tampered, or expired, execution is strictly denied.

3. **Grounded Fact Retrieval & Real-Time State Tracking**:
   Read tools execute immediately and return verified live state. All operations are logged to a tamper-evident **Enterprise Audit Trail**.

---

## Technology Stack

- **Frontend**: React 18, TypeScript, Vite, Tailwind CSS, Lucide Icons, Axios.
- **Backend**: Python 3.13, FastAPI, Pydantic v2, SQLAlchemy 2.0 (asyncio), Uvicorn.
- **Agentic AI**: LangGraph, StateGraph, persistent state checkpointer, structured tool discovery.
- **MCP Integration**: FastMCP 4.1.0, official Anthropic MCP Python SDK 2.3.0.
- **Database**: PostgreSQL (asyncpg) / SQLite (aiosqlite) zero-setup dev fallback.
- **Security**: Cryptographic HMAC-SHA256 tokens, bcrypt password hashing, JWT RBAC (Admin, Operator, Viewer).

---

## Quick Start (Local Development)

### 1. Prerequisites
- Python 3.11+ (Python 3.13 verified)
- Node.js v18+ (Node v24 verified) & npm
- Git

### 2. Backend Setup
```powershell
# In project root:
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload --app-dir backend
```
Or run the convenience script:
```powershell
.\scripts\run_backend.ps1
```
The FastAPI backend will start at `http://localhost:8000`. Swagger API docs are available at `http://localhost:8000/docs`.

### 3. Frontend Setup
```powershell
cd frontend
npm install
npm run dev
```
Or run the convenience script:
```powershell
.\scripts\run_frontend.ps1
```
The React frontend will start at `http://localhost:5173`.

---

## Demo Credentials

OpsPilot seeds two enterprise test users by default:
- **Enterprise Admin**: `admin@opspilot.internal` / `admin123` (Full permissions)
- **DevOps Operator**: `operator@opspilot.internal` / `operator123` (Action approval allowed)

---

## End-to-End Scenarios

OpsPilot implements all 6 official master operational scenarios:

| Scenario | User Request | Expected Behavior |
|---|---|---|
| **Scenario A** | *"Show me all open operational incidents from the database."* | Discovers PostgreSQL MCP server, calls `list_incidents`, returns grounded incident IDs and severities. |
| **Scenario B** | *"Check the open issues in my repository and identify highest-priority problems."* | Discovers GitHub MCP server, calls `list_issues`, extracts titles and labels. |
| **Scenario C** | *"Create a GitHub issue for fixing the authentication timeout."* | Discovers `create_issue`, drafts ticket, **PAUSES** at approval gate. Approving creates the ticket and returns verified URL. |
| **Scenario D** | *"Find important unread emails related to deployment problems."* | Discovers Productivity MCP server, queries `get_unread_messages`, summarizes unread emails. |
| **Scenario E** | *"Draft an email to the engineering team about the deployment delay."* | Discovers `create_email_draft` / `send_email`, requires explicit human review and approval. |
| **Scenario F** | *"Schedule a meeting with the development team tomorrow at 3 PM."* | Checks `check_availability` for slot conflicts, drafts `create_calendar_event`, halts for approval. |

---

## Running the Automated Test Suite

OpsPilot includes 14 automated pytest integration and security tests:
```powershell
.\.venv\Scripts\pytest.exe -v backend/tests
```

Test coverage includes:
- FastMCP tool discovery across all 3 custom servers
- Database read operations and seed data verification
- Approval boundary rejection on unapproved write calls
- Parameter tampering detection via canonical SHA-256 action hashing
- Forged approval token rejection
- Single-use and expiration enforcement
- LangGraph agent routing and write interruption

---

## License & Compliance

Built for enterprise operational workflows with zero unauthorized write execution.
*Note: Remote Git pushes are disabled locally until final project sign-off.*
