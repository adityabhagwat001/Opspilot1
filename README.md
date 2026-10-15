# OpsPilot — Enterprise Agentic AI Platform
> **Live Company Integrations via FastMCP • PostgreSQL • GitHub Intelligence • LangGraph • Cryptographic Human Approval Boundary**

OpsPilot is a centralized enterprise AI operations assistant engineered for Agentic AI Engineers and Solutions Architects. It connects to live company systems (PostgreSQL operational databases, GitHub repositories, company email, and calendars) through custom **Model Context Protocol (MCP)** servers built on **FastMCP**, augmented with real-time **GitHub Intelligence & AI DevOps**.

---

## Key Architectural Principles

1. **Acts on Live Systems via Custom FastMCP Servers**:
   OpsPilot does not call arbitrary external scripts; it discovers and invokes tools strictly across custom FastMCP integration servers:
   - **PostgreSQL FastMCP Server** (`mcp_servers/postgres_server/`): Live operational incidents, tasks, entities, and status machines.
   - **GitHub FastMCP Server** (`mcp_servers/github_server/`): Issues, pull requests, commits, workflow runs, failed jobs, build logs, file inspection, branch management, and atomic fix pull-request generation.
   - **Productivity FastMCP Server** (`mcp_servers/productivity_server/`): Mailbox search, unread query, email drafting/sending, and calendar conflict detection/scheduling.

2. **Mandatory Human-in-the-Loop Write Approval Boundary**:
   **The AI model NEVER receives authority to write to external systems directly.**
   - When a write action is proposed (`create_issue`, `send_email`, `create_calendar_event`, `create_branch`, `commit_file_changes`, `create_pull_request`, `rerun_workflow`), the backend halts execution.
   - A canonical cryptographic action hash (`SHA-256`) is computed from canonical arguments.
   - An approval ticket is persisted with a 15-minute expiration window and single-use nonce.
   - A human reviewer inspects the exact proposed action, target branch, and patch diff in the **Approval Center**.
   - Upon approval, the backend issues an unforgeable, 4-part HMAC-signed approval token (`timestamp.action_hash.nonce.signature`).
   - The FastMCP server verifies the signature and single-use nonce before executing the tool.
   - If rejected, tampered, expired, or replayed, execution is strictly denied.

3. **Grounded Fact Retrieval & Real-Time State Tracking**:
   Read tools execute immediately and return verified live state. All operations are logged to a tamper-evident **Enterprise Audit Trail**.

---

## Real-Time GitHub Intelligence & AI DevOps Features

OpsPilot includes an autonomous GitHub Intelligence & AI DevOps module designed for real-time monitoring, failure diagnosis, and verified patch remediation:

### 1. GitHub Connect & Verified Telemetry
- Supports GitHub Personal Access Tokens (PAT) and GitHub Apps.
- Displays verified connected account identity, avatar, public/private repository counts, and OAuth token scopes.
- Zero-setup local mock sandbox mode for air-gapped demo environments.

### 2. Live Activity Ledger & Webhook Ingestion
- Real-time ingestion endpoint (`POST /api/github/webhook`).
- **HMAC-SHA256 signature verification** (`X-Hub-Signature-256`) against `GITHUB_WEBHOOK_SECRET`.
- **Idempotent deduplication** via `X-GitHub-Delivery` prevents replay attacks and duplicate alerts.
- Live stream of push events, pull requests, workflow runs, and issue activities.

### 3. Automated CI/CD Failure Detection
- Automatically detects failing GitHub Actions runs (`workflow_run.completed` with `conclusion: failure`).
- Fetches failing jobs, identifies the exact failing pipeline step, extracts relevant error snippets, and creates an incident record.

### 4. AI Error Root-Cause Analysis
- Inspects build and test traces (e.g., Python `ModuleNotFoundError`, TypeScript compiler errors, pytest assertion failures).
- Analyzes probable root causes, synthesizes supporting evidence, and provides confidence levels and limitations.

### 5. AI Patch Proposal Generation
- Formulates isolated code patches with unified Git diffs.
- Binds patch proposals to dedicated, non-default fix branches (e.g. `opspilot-fix/ci-remediation-run-<id>`).
- Calculates affected files and displays unified patch diffs with syntax highlighting.

### 6. Cryptographic Human Approval Integration
- Fix proposals automatically generate a pending ticket in the **Enterprise Approval Center**.
- Zero write operations occur without explicit operator approval.

### 7. Verified Automated Fix Execution & Pull Request Creation
- Creates the dedicated fix branch on GitHub.
- Commits patch files safely via the GitHub Trees & Commits API.
- Opens a GitHub Pull Request targeting the base branch (default: `main`).
- Never pushes directly to protected default branches. Never automatically merges PRs.

### 8. In-App Notifications & Real-Time Alerts
- Live alerts for newly detected pipeline failures, generated fix proposals, and executed pull requests.
- Mark individual notifications or all notifications as read.

### 9. Repository Health Scoring
- Documented health metric formula: `Score = 100 - (Active Failures * 15)`.
- Status categorization: `OPTIMAL` (100%), `WARNING` (50–85%), `CRITICAL` (<50%).

---

## FastMCP GitHub Tool Registry

The GitHub FastMCP server exposes 17 tools categorized into safe read operations and protected write operations:

| Tool Name | Type | Access Level | Description |
|---|---|---|---|
| `get_authenticated_user` | Read | Safe | Retrieves authenticated GitHub user profile and permissions. |
| `list_repositories` | Read | Safe | Lists authorized repositories for the authenticated user/org. |
| `get_repository` | Read | Safe | Fetches detailed metadata for a specific repository. |
| `list_commits` | Read | Safe | Lists recent commit history for a repository and branch. |
| `list_pull_requests` | Read | Safe | Lists open or closed pull requests with reviewer status. |
| `get_pull_request_diff` | Read | Safe | Retrieves raw unified diff for a pull request. |
| `list_workflow_runs` | Read | Safe | Lists recent GitHub Actions workflow runs and conclusions. |
| `get_workflow_run` | Read | Safe | Retrieves full metadata and timing for a specific run. |
| `list_workflow_run_jobs` | Read | Safe | Retrieves jobs and individual execution steps for a run. |
| `get_workflow_logs` | Read | Safe | Fetches and extracts failing error snippets from run logs. |
| `get_repository_file` | Read | Safe | Retrieves file contents and SHA from a repository branch. |
| `create_branch` | Write | **Approval Gated** | Creates a new branch from a specified base commit/branch. |
| `commit_file_changes` | Write | **Approval Gated** | Commits one or more file updates to a branch. |
| `create_pull_request` | Write | **Approval Gated** | Creates fix branch, commits patch files, and opens PR. |
| `create_issue` | Write | **Approval Gated** | Opens an issue with labels and markdown body. |
| `add_issue_comment` | Write | **Approval Gated** | Posts a review comment or update to an issue/PR. |
| `rerun_workflow` | Write | **Approval Gated** | Re-triggers a failed GitHub Actions workflow run. |

---

## Technology Stack

- **Frontend**: React 19, TypeScript, Vite 8, Tailwind CSS, Lucide Icons, Axios.
- **Backend**: Python 3.13, FastAPI, Pydantic v2, SQLAlchemy 2.0 (asyncio), Uvicorn.
- **Agentic AI**: LangGraph, StateGraph, persistent checkpointer, dynamic FastMCP tool router.
- **MCP Integration**: FastMCP 4.1.0, official Anthropic MCP Python SDK 2.3.0.
- **Database**: PostgreSQL (asyncpg) / SQLite (aiosqlite) zero-setup fallback with additive schema migrations.
- **Security**: 4-part HMAC-SHA256 tokens, single-use nonces, bcrypt, JWT RBAC (Admin, Operator, Viewer).

---

## Quick Start (Local Development)

### 1. Backend Setup
```powershell
# From project root:
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload --app-dir backend
```
Backend API will start at `http://localhost:8000`. Interactive OpenAPI documentation is at `http://localhost:8000/docs`.

### 2. Frontend Setup
```powershell
cd frontend
npm run dev
```
Frontend will start at `http://localhost:5173`.

---

## Running the Automated Test Suite

OpsPilot includes **31 automated pytest integration and regression tests** with 100% pass rate:
```powershell
.\.venv\Scripts\pytest.exe -v backend/tests
```

### Test Suite Inventory:
1. `backend/tests/test_approval_security.py` (5 tests): Deterministic SHA-256 action hashing, parameter tampering detection, forged token rejection, genuine token verification, approval lifecycle.
2. `backend/tests/test_github_intelligence.py` (6 tests): GitHub account telemetry, repository discovery & monitoring toggle, webhook signature validation, failure detection, AI error analysis, patch proposal generation, PR execution, health telemetry.
3. `backend/tests/test_langgraph_agent.py` (5 tests): Read tool routing, write interrupt boundaries, greeting handling, out-of-scope query handling, contextual issue creation.
4. `backend/tests/test_mcp_servers.py` (9 tests): FastMCP tool discovery across PostgreSQL, Productivity, and GitHub servers; extended read and write tools.
5. `backend/tests/test_rbac_and_replay_boundary.py` (6 tests): 401 unauthenticated protection, viewer write prohibition, workspace isolation, single-use nonce replay defense, parameter modification invalidation.

---

## GitHub Webhook Configuration Guide

To configure real GitHub Webhooks for production repositories:
1. Open your repository on GitHub -> **Settings** -> **Webhooks** -> **Add webhook**.
2. **Payload URL**: `https://<your-opspilot-domain>/api/github/webhook`
3. **Content type**: `application/json`
4. **Secret**: Enter the value configured in `GITHUB_WEBHOOK_SECRET` in your `.env`.
5. **Events**: Select **Let me select individual events**:
   - `Pushes`
   - `Pull requests`
   - `Workflow runs`
   - `Issues`
6. Click **Add webhook**. OpsPilot will verify incoming signatures via `X-Hub-Signature-256` and ingest events into the live activity ledger.
