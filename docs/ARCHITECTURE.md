# OpsPilot System Architecture

## 1. Executive Summary

**OpsPilot** is an AI-assisted Cloud Infrastructure & DevOps Reliability Platform. It provides real-time telemetry monitoring, automated anomaly detection, AI-powered root cause analysis (RCA), and safe, auditable runbook remediation for distributed servers, Docker containers, and cloud infrastructure.

---

## 2. High-Level Architectural Diagram

```
+-----------------------------------------------------------------------------------+
|                                  CLIENT LAYER                                     |
|                                                                                   |
|  +-----------------------------------------------------------------------------+  |
|  |                 OpsPilot SRE Console (Vite + React + TypeScript)            |  |
|  |     - Live Telemetry Dashboard   - Incident Triage Board   - Runbook Terminal|  |
|  +-----------------------------------------------------------------------------+  |
+------------------------------------------^----------------------------------------+
                                           | HTTP (REST) / WebSocket (WSS)
                                           v
+-----------------------------------------------------------------------------------+
|                             API GATEWAY & BACKEND LAYER                           |
|                                                                                   |
|  +-----------------------------------------------------------------------------+  |
|  |                     FastAPI Asynchronous Gateway & Core                     |  |
|  |                                                                             |  |
|  |   [Auth & RBAC Middleware]        [Rate Limiting (Token Bucket)]            |  |
|  |   [Telemetry Ingestion Engine]    [Incident Evaluation Pipeline]            |  |
|  |   [WebSocket Stream Dispatcher]   [Audit Logging Service]                   |  |
|  +-----------------------------------------------------------------------------+  |
+-----------------^-------------------------^--------------------------^------------+
                  |                         |                          |
                  v                         v                          v
+-----------------------------+ +-----------------------+ +-------------------------+
|      DATA & CACHE LAYER     | |     AI & RAG ENGINE   | |     EXECUTION ENGINE    |
|                             | |                       | |                         |
|  - PostgreSQL:              | | - Vector Store:       | | - Runbook Sandbox:      |
|    Users, Nodes, Incidents, | |   ChromaDB / FAISS    | |   Dry-run / Step-by-step|
|    Audit Logs, Runbooks     | | - LLM Orchestrator:   | |   Command executor      |
|  - Redis:                   | |   Incident Diagnosis  | | - Approval Gatekeeper:  |
|    Telemetry stream cache,  | |   & Log Synthesis     | |   Human-in-the-loop for |
|    Rate limiting tokens,    | | - Runbook Retrieval:  | |   high-risk operations  |
|    Live node heartbeat TTL  | |   Domain embeddings   | |                         |
+-----------------------------+ +-----------------------+ +-------------------------+
                  ^
                  | Ingestion over HTTPS / mTLS
                  |
+-----------------+-----------------------------------------------------------------+
|                                 TELEMETRY PROBES LAYER                            |
|                                                                                   |
|  +-------------------------+  +--------------------------+  +------------------+  |
|  | Node Daemon (psutil)    |  | Docker Container Monitor |  | Custom Webhooks  |  |
|  | CPU, RAM, Disk, Network |  | Container stats & logs   |  | App Healthchecks |  |
|  +-------------------------+  +--------------------------+  +------------------+  |
+-----------------------------------------------------------------------------------+
```

---

## 3. Core Component Responsibilities

### 3.1 Telemetry Collector Probes (`agents/`)
- **Lightweight Daemon:** Minimal resource footprint (<25MB RAM, <1% CPU).
- **Metric Extraction:** Measures host CPU utilization, memory pressure, disk I/O, network bandwidth, and container states.
- **Resilient Transport:** Batches metrics and employs exponential backoff retry mechanisms when network connectivity to the central server is intermittent.

### 3.2 FastAPI Core Backend (`backend/`)
- **Asynchronous I/O:** Leverages Python's `asyncio` loop to handle high-concurrency metric packet ingestion.
- **Incident Rule Evaluator:** Continuously computes moving averages and thresholds (e.g., CPU sustained above 90% for > 3 minutes, disk saturation > 95%).
- **WebSocket Streaming Engine:** Pushes live metric frames to connected frontend clients without continuous HTTP polling.
- **Structured Audit Logging:** Every configuration change, incident acknowledgment, and runbook trigger is written to an append-only audit trail.

### 3.3 AI Diagnostics Subsystem (`ai_engine/`)
- **Context Synthesizer:** Aggregates error logs, recent infrastructure metric anomalies, and system topology into structured incident contexts.
- **Runbook RAG Pipeline:** Indexes past post-mortems and standard operating procedures (SOPs) into a local vector database to recommend targeted recovery steps.
- **Root Cause Analysis (RCA):** Outputs confidence-ranked diagnoses and proposed remediation commands.

### 3.4 SRE Web Console (`frontend/`)
- **Real-time Reactive UI:** Developed with modern React and TypeScript for strong type safety and predictable state handling.
- **Operational Ergonomics:** High-contrast dark-mode observability palette designed to reduce cognitive load during incident triage.
- **Interactive Runbook Runner:** Step-by-step visual execution flow with clear diffs and output logs.

---

## 4. Data Flow & Lifecycle

```
[Agent Probe] 
     │ (Heartbeat / Telemetry Frame every 5s)
     ▼
[Ingestion API] ──► [Redis Live TTL Cache]
     │
     ├──► [Threshold Evaluator] ──► (Anomaly Detected?) ──► [Create Incident Record]
     │                                                               │
     │                                                               ├──► [Trigger AI RCA]
     │                                                               └──► [Emit WebSocket Alert]
     ▼
[TimescaleDB / Postgres Archive]
```

---

## 5. Security & Threat Modeling

1. **Authentication & Authorization:** Secure JWT access tokens with short TTLs and secure HTTP-only refresh tokens. Role-Based Access Control (Admin, Operator, Viewer).
2. **Agent Verification:** Unique Node API Keys with rotation support to prevent unauthorized metric forgery.
3. **Command Sanitization:** Runbook commands are restricted to whitelisted templates and parameter schemas to prevent arbitrary remote code execution (RCE).
4. **Audit Trail:** Append-only log of every administrative and automated action.
