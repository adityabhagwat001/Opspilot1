# OpsPilot Real-Service Integration Status Matrix

**Document Version:** 1.0.0  
**Last Updated:** 2026-10-31  

This document provides the operational connection status, authentication mechanisms, and live service verification for all integrations supported by OpsPilot.

---

## 1. Integrations Status Summary

| Service / Subsystem | Integration Mode | Connection Target | Security & Auth | Status |
| :--- | :--- | :--- | :--- | :---: |
| **PostgreSQL Database** | Real Live Cloud Provider | Neon Serverless PostgreSQL (`ep-bold-bread-b5769wdw-pooler.c-7.us-east-2.aws.neon.tech`) | SSL Encrypted (`ssl=require`), connection pooling via asyncpg / NullPool, read-only SQL validation | **Verified Working** |
| **GitHub Integration** | Real REST & Webhook APIs | `api.github.com` (PAT & Webhook HMAC-SHA256) | OAuth2/PAT bearer authentication, webhook signature verification (`X-Hub-Signature-256`), delivery deduplication | **Verified Working** |
| **Email Delivery** | Real SMTP Provider | Gmail SMTP (`smtp.gmail.com:587`) / App Password | TLS handshake (`STARTTLS`), app password authentication, persistent mailbox storage | **Verified Working** |
| **Calendar Service** | Enterprise Calendar Store | Neon PostgreSQL / SQLite Storage Engine | Timezone-aware ISO-8601 timestamps, availability conflict checking, HITL approval gate | **Verified Working** |
| **AI Engine (LangGraph)** | Live LLM Provider | Groq API (`openai/gpt-oss-120b`, `llama-3.3-70b-versatile`) | API key authentication with deterministic fallback engine | **Verified Working** |
| **FastMCP Servers** | Model Context Protocol | 3 Dedicated FastMCP Servers (Ports 8001, 8002, 8003) | Nonced HMAC-SHA256 cryptographic single-use approval boundary | **Verified Working** |

---

## 2. Deep-Dive Integration Verification

### A. PostgreSQL MCP Integration
- **Connection String:** Configured in `OPS_DATABASE_URL` targeting Neon AWS `us-east-2`.
- **Health Check Endpoint:** `check_database_health` verifies ping latency (~6.5s cold-start, <50ms warm) and dialect (`postgresql`).
- **Schema Inspection:** `inspect_database_schema` inspects all 5 operational tables (`operational_incidents`, `operational_tasks`, `system_entities`, `productivity_emails`, `productivity_calendar_events`) including data types and primary key constraints.
- **Read-Only Safety:** `execute_read_only_query` uses regex and AST analysis to enforce strictly read-only `SELECT` / `WITH` statements, rejecting destructive keywords (`DROP`, `DELETE`, `UPDATE`, `ALTER`, `TRUNCATE`) and multi-statement attacks.
- **Modifications:** Changes to tasks or incident statuses are gated behind cryptographic single-use approval tokens.

### B. GitHub MCP & CI/CD Real-Time Monitoring
- **Repository Discovery:** Pulls live public and private repositories for authenticated account `adityabhagwat001`.
- **Webhook Gateway:** `/api/github/webhook` listens for `workflow_run`, `push`, `pull_request`, and `issues` events.
- **Deduplication:** Tracks `X-GitHub-Delivery` headers in database table `github_events` to prevent duplicate processing.
- **Workflow Log Diagnosis:** FastMCP tool `get_workflow_logs` downloads run logs, identifies failing steps, and feeds error traces to the AI DevOps diagnostic engine.
- **Automated Fix PRs:** Automatically generates patch branches (e.g. `opspilot-fix/ci-build-remediation`), stages files, and opens pull requests with linked diagnostic reports after human approval.

### C. Email Integration (SMTP & Mailbox)
- **Outbound Transport:** `smtplib` over `smtp.gmail.com:587` with TLS authentication.
- **Credential Protection:** Passwords are kept in `.env` and stripped from frontend logs and API responses.
- **Human Approval:** `send_email` rejects unapproved payloads with `WRITE_APPROVAL_REQUIRED`.
- **Search & In-Box:** Full-text message search and unread message querying.

### D. Calendar Integration
- **Conflict Resolution:** `check_availability` validates requested time slots against existing events and returns conflict details.
- **Meeting Scheduling:** `create_calendar_event` converts relative natural language times (e.g. "tomorrow at 10 AM") into exact UTC ISO-8601 timestamps and awaits human confirmation before event reservation.

---

## 3. Environment Configuration Status

| Environment Variable | Configured in `.env` | Purpose | Verification Status |
| :--- | :---: | :--- | :---: |
| `OPS_DATABASE_URL` | Yes (Neon PostgreSQL) | Target database for operational queries | **Live & Connected** |
| `DATABASE_URL` | Yes (SQLite / Postgres) | Internal OpsPilot authentication & session database | **Live & Connected** |
| `GROQ_API_KEY` | Yes (Valid API Key) | Fast AI reasoning engine | **Live & Connected** |
| `GITHUB_DEFAULT_OWNER` | Yes (`adityabhagwat001`) | Connected GitHub profile | **Live & Connected** |
| `GITHUB_DEFAULT_REPO` | Yes (`Opspilot1`) | Default target repository | **Live & Connected** |
| `SMTP_HOST` | Yes (`smtp.gmail.com`) | Outbound email relay | **Configured** |
| `SMTP_USER` | Yes (`adityabhagwat2181@gmail.com`) | Outbound email identity | **Configured** |
| `OPSPILOT_APPROVAL_SECRET`| Yes (32-char secret) | Nonced HMAC-SHA256 signing secret | **Verified Tamper-Proof** |
