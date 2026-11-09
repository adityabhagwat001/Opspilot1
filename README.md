# OpsPilot — Enterprise Agentic AI Platform
> **Live Company Integrations via FastMCP • PostgreSQL • GitHub Intelligence • LangGraph • Cryptographic Human Approval Boundary**

OpsPilot is a centralized enterprise AI operations assistant engineered for Agentic AI Engineers, Solutions Architects, and DevOps Teams. It connects to live company systems (PostgreSQL operational databases, GitHub repositories, company email, and calendars) through custom **Model Context Protocol (MCP)** servers built on **FastMCP**, augmented with real-time **GitHub Intelligence & AI DevOps**.

---

## AlgoProfessor OpsPilot Requirements Compliance Checklist

| Mandatory Requirement | Status | Verification Detail |
| :--- | :---: | :--- |
| **Natural Language Agent & Intent Classification** | **Verified Working** | LangGraph StateGraph agent routes intents across PostgreSQL, GitHub, Email, and Calendar systems with multi-turn context retention. |
| **GitHub Live Operations & Repository Discovery** | **Verified Working** | Connects to authenticated GitHub profiles (`adityabhagwat001`), lists repositories, commits, pull requests, issues, and workflow runs via live GitHub REST API. |
| **CI/CD Failure Detection & Log Diagnosis** | **Verified Working** | Webhook gateway & polling detects failing workflow runs, retrieves raw job logs, extracts error traces, and synthesizes root-cause diagnoses. |
| **Safe AI-Assisted Error Fixing & PR Creation** | **Verified Working** | Formulates isolated patches on dedicated fix branches (e.g. `opspilot-fix/...`), stages diffs, and opens pull requests strictly after human approval. Never pushes directly to default branches. |
| **PostgreSQL Live Connection & Schema Inspection** | **Verified Working** | Connected to live Neon Serverless PostgreSQL (`ep-bold-bread-b5769wdw-pooler...`). Exposes `inspect_database_schema`, `execute_read_only_query`, and `check_database_health`. |
| **Safe Read-Only SQL & Dangerous DDL/DML Rejection** | **Verified Working** | AST & regex safe query validator enforces single `SELECT`/`WITH` statements with row limits; blocks `DROP`, `DELETE`, `UPDATE`, `INSERT`, `ALTER`, `TRUNCATE`, and multi-statement attacks. |
| **Email Integration (SMTP & Mailbox)** | **Verified Working** | Live SMTP dispatch (`smtp.gmail.com:587` with TLS) for approved outgoing emails; persistent operational mailbox storage for message searches and triage. |
| **Calendar Scheduling & Conflict Detection** | **Verified Working** | Timezone-aware ISO-8601 availability conflict detection (`check_availability`) and human-gated meeting scheduling (`create_calendar_event`). |
| **Cryptographic Human Approval Boundary (HITL)** | **Verified Working** | All write mutations require unforgeable, 4-part HMAC-SHA256 tokens (`timestamp.action_hash.nonce.signature`) with 15-minute TTL. Single-use nonces prevent replay attacks. |
| **Enterprise RBAC & Security** | **Verified Working** | JWT authentication with role-based access control (`admin`, `operator`, `viewer`) and cross-workspace tenant isolation (`default-ops`). |
| **Dashboard UI & Simplified Plain-Text Cards** | **Verified Working** | Production React 19 UI with real-time telemetry, clear connection statuses, and human-readable Approval Cards detailing: *What is the Issue?*, *Proposed AI Solution*, and *How It Was Solved & Changes Applied*. |
| **Automated Test Coverage** | **Verified Working** | **38 of 38 automated integration and regression tests passing (100%)** across 5 test suites. |

---

## Key Architectural Principles

1. **Acts on Live Systems via Custom FastMCP Servers**:
   OpsPilot does not invoke arbitrary external shell scripts; it discovers and invokes tools strictly across custom FastMCP integration servers:
   - **PostgreSQL FastMCP Server** (`mcp_servers/postgres_server/`): Live operational incidents, tasks, entities, schema inspection, read-only SQL queries, and health ping.
   - **GitHub FastMCP Server** (`mcp_servers/github_server/`): Issues, pull requests, commits, workflow runs, failed jobs, build logs, file inspection, branch management, and atomic fix pull-request generation.
   - **Productivity FastMCP Server** (`mcp_servers/productivity_server/`): Mailbox search, unread query, live SMTP email dispatch, and calendar conflict detection/scheduling.

2. **Mandatory Human-in-the-Loop Write Approval Boundary**:
   **The AI model NEVER receives authority to write to external systems directly.**
   - When a write action is proposed (`create_issue`, `send_email`, `create_calendar_event`, `create_branch`, `commit_file_changes`, `create_pull_request`, `rerun_workflow`), the backend halts execution.
   - A canonical cryptographic action hash (`SHA-256`) is computed from canonical arguments.
   - An approval ticket is persisted with a 15-minute expiration window and single-use nonce.
   - A human reviewer inspects the proposed action in the **Approval Center** or **Chat UI**.
   - Upon approval, the backend issues an unforgeable, 4-part HMAC-signed approval token (`timestamp.action_hash.nonce.signature`).
   - The FastMCP server verifies the signature and single-use nonce before executing the tool.
   - If rejected, tampered, expired, or replayed, execution is strictly denied.

3. **Grounded Fact Retrieval & Real-Time State Tracking**:
   Read tools execute immediately and return verified live state. All operations are logged to a tamper-evident **Enterprise Audit Trail**.

---

## Real-Time GitHub Intelligence & AI DevOps

1. **GitHub Connect & Telemetry**:
   - Live profile connection with OAuth/PAT token scopes.
   - Real-time repository discovery and activity streaming.

2. **Webhook Ingestion**:
   - Endpoint: `POST /api/github/webhook`.
   - **HMAC-SHA256 signature validation** (`X-Hub-Signature-256`) against `GITHUB_WEBHOOK_SECRET`.
   - **Deduplication** via `X-GitHub-Delivery` prevents duplicate alerts.

3. **Automated CI/CD Failure Detection & Fix Lifecycle**:
   - Detects failing GitHub Actions runs (`workflow_run.completed` with `conclusion: failure`).
   - Retrieves error logs and identifies the failing step.
   - Synthesizes root-cause diagnosis.
   - Generates unified Git patch on an isolated fix branch (`opspilot-fix/...`).
   - Awaits human approval.
   - Upon approval, creates the fix branch, commits the patch, and opens a Pull Request.

---

## Technology Stack

- **Frontend**: React 19, TypeScript, Vite 8, Tailwind CSS, Lucide Icons, Axios.
- **Backend**: Python 3.13, FastAPI, Pydantic v2, SQLAlchemy 2.0 (asyncio), Uvicorn.
- **Agentic AI**: LangGraph, StateGraph, persistent memory checkpointer, Groq LLM API.
- **MCP Framework**: FastMCP 4.1.0, official Anthropic MCP Python SDK 2.3.0.
- **Database**: PostgreSQL (asyncpg, Neon cloud) with SQLite (aiosqlite) zero-setup fallback.
- **Security**: 4-part HMAC-SHA256 tokens, single-use nonces, bcrypt, JWT RBAC (`admin`, `operator`, `viewer`).

---

## Quick Start (Local Development)

### 1. Prerequisites
- Python 3.11+ (Python 3.13 recommended)
- Node.js 18+ and npm
- PostgreSQL database (or automatic SQLite fallback)

### 2. Environment Configuration
Copy `.env.example` to `.env`:
```powershell
cp .env.example .env
```
Ensure `OPS_DATABASE_URL`, `GROQ_API_KEY`, and `GITHUB_DEFAULT_OWNER` are populated.

### 3. Backend Startup
```powershell
# From project root:
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload --app-dir backend
```
Backend API will start at `http://localhost:8000`. OpenAPI documentation is available at `http://localhost:8000/docs`.

### 4. FastMCP Servers Startup (Optional Background Daemons)
FastMCP microservices run automatically in-process via `mcp_router.py`, or can be launched as dedicated background network services:
```powershell
# Terminal 1 - PostgreSQL MCP Server
.\.venv\Scripts\python.exe mcp_servers/postgres_server/server.py

# Terminal 2 - GitHub MCP Server
.\.venv\Scripts\python.exe mcp_servers/github_server/server.py

# Terminal 3 - Productivity MCP Server
.\.venv\Scripts\python.exe mcp_servers/productivity_server/server.py
```

### 5. Frontend Startup
```powershell
cd frontend
npm install
npm run dev
```
Frontend will start at `http://localhost:5173`.

---

## Running Automated Tests

OpsPilot includes **38 automated pytest integration and regression tests** with 100% pass rate:
```powershell
.\.venv\Scripts\pytest.exe -v backend/tests
```

### Test Suite Inventory:
1. `backend/tests/test_approval_security.py` (5 tests): Deterministic SHA-256 action hashing, parameter tampering detection, forged token rejection, genuine token verification, approval lifecycle.
2. `backend/tests/test_github_intelligence.py` (6 tests): GitHub account telemetry, repository discovery & monitoring toggle, webhook signature validation, failure detection, AI error analysis, patch proposal generation, PR execution, health telemetry.
3. `backend/tests/test_langgraph_agent.py` (8 tests): Read tool routing, write interrupt boundaries, greeting handling, out-of-scope query handling, contextual issue creation, safe SQL database queries, database schema inspection, GitHub activities query.
4. `backend/tests/test_mcp_servers.py` (13 tests): FastMCP tool discovery across PostgreSQL, Productivity, and GitHub servers; schema inspection; safe SQL queries; dangerous DDL/DML rejection; database health latency ping; email & calendar approval gates.
5. `backend/tests/test_rbac_and_replay_boundary.py` (6 tests): 401 unauthenticated protection, viewer write prohibition, workspace isolation, single-use nonce replay defense, parameter modification invalidation.

---

## Production Deployment Guide

### Option 1: Docker Compose Deployment
```yaml
# docker-compose.yml
version: '3.8'
services:
  backend:
    build:
      context: .
      dockerfile: Dockerfile.backend
    environment:
      - ENVIRONMENT=production
      - DATABASE_URL=postgresql+asyncpg://user:pass@db:5432/opspilot
      - OPS_DATABASE_URL=postgresql+asyncpg://user:pass@db:5432/operations
    ports:
      - "8000:8000"
    restart: always

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile.frontend
    ports:
      - "80:80"
    restart: always
```

### Option 2: Systemd & Reverse Proxy (NGINX)
1. Build frontend bundle: `cd frontend && npm run build`.
2. Configure NGINX to serve `frontend/dist` as static assets and proxy `/api/*` to `http://127.0.0.1:8000`.
3. Set up Systemd service for FastAPI Uvicorn backend with 4 workers.
4. Enable HTTPS via Let's Encrypt / Certbot.

---

## Default Test & Production Accounts

| Role | Email | Password | Access Level |
| :--- | :--- | :--- | :--- |
| **Enterprise Admin** | `admin@opspilot.internal` | `admin123` | Full administrative control, all write approval authority, audit ledger access. |
| **DevOps Operator** | `operator@opspilot.internal` | `operator123` | Operational queries, fix proposal generation, approved PR creation. |
