# OpsPilot 🛰️
### Intelligent Cloud Infrastructure & AI Reliability Platform

[![CI Pipeline](https://github.com/adityabhagwat/opspilot/actions/workflows/ci.yml/badge.svg)](https://github.com/adityabhagwat/opspilot/actions)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-19+-61DAFB.svg?logo=react&logoColor=black)](https://react.dev)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.9+-3178C6.svg?logo=typescript&logoColor=white)](https://www.typescriptlang.org)
[![Python](https://img.shields.io/badge/Python-3.12%20%7C%203.13-3776AB.svg?logo=python&logoColor=white)](https://www.python.org)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

OpsPilot is a production-grade, AI-assisted Cloud Infrastructure & Site Reliability Engineering (SRE) platform. It continuously ingests system telemetry, detects infrastructure anomalies, performs AI-powered Root Cause Analysis (RCA) on logs, and safely triggers automated runbook remediation with human-in-the-loop controls.

---

## 🏛️ System Architecture

OpsPilot is engineered around a decoupled polyglot architecture:

```
+-----------------------------------------------------------------------------------+
|                           OPSPILOT SRE WEB CONSOLE                                |
|             React 19 + TypeScript + Vite + Observability Dark Theme               |
+------------------------------------------^----------------------------------------+
                                           | REST / WebSocket
                                           v
+-----------------------------------------------------------------------------------+
|                        FASTAPI ASYNCHRONOUS GATEWAY                               |
|        - Auth & RBAC               - Anomaly Evaluation                           |
|        - Metric Ingestion Engine   - WebSocket Live Broadcasts                    |
+-----------------^-------------------------^--------------------------^------------+
                  |                         |                          |
                  v                         v                          v
+-----------------------------+ +-----------------------+ +-------------------------+
|     POSTGRESQL & REDIS      | |    AI & RAG ENGINE    | |     RUNBOOK SANDBOX     |
| - Users, Nodes, Incidents   | | - ChromaDB Embeddings | | - Step-by-step executor |
| - High-throughput TTL cache | | - LLM Root Cause RCA  | | - Approval Gatekeeper   |
+-----------------------------+ +-----------------------+ +-------------------------+
                  ^
                  | Ingestion over HTTPS
+-----------------+-----------------------------------------------------------------+
|                       LIGHTWEIGHT TELEMETRY AGENT PROBES                          |
|         Bare-metal servers, Docker hosts, Kubernetes node daemons (psutil)        |
+-----------------------------------------------------------------------------------+
```

Detailed architectural diagrams and threat modeling are documented in [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

---

## 📅 3-Month / 15-Sprint Engineering Roadmap

OpsPilot is structured across a **15-Sprint Roadmap (5–6 days per sprint)** to align with continuous evaluation cycles:

| Phase | Sprints | Focus |
|---|---|---|
| **Phase 1: Foundation & Telemetry Core** | Sprints 1 – 5 | Architecture, DB Schemas, Ingestion API, WebSocket streaming, MVP Review |
| **Phase 2: AI Diagnostics & Runbooks** | Sprints 6 – 10 | Log Parser, LLM/RAG RCA Engine, Sandbox Runbooks, Container Monitoring |
| **Phase 3: Production & Security** | Sprints 11 – 15 | Cost Analytics, Audit Logs, Rate Limiting, Chaos Testing, Cloud Deploy |

Full roadmap breakdown and milestone deliverables: [`docs/ROADMAP.md`](docs/ROADMAP.md).

---

## 🚀 Sprint 1 Deliverables (Current Milestone: `v0.1.0-alpha.1`)

- [x] **Architecture Specifications:** Complete design documents in [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) and [`docs/API_SPEC.md`](docs/API_SPEC.md).
- [x] **Architectural Decision Record (ADR):** Polyglot architecture rationale in [`docs/adr/0001-polyglot-architecture.md`](docs/adr/0001-polyglot-architecture.md).
- [x] **Backend Core Skeleton:** Layered FastAPI service with async configuration, Pydantic schemas, and structured logging.
- [x] **Real-Time Host Diagnostics Probe:** Working `/api/v1/health` and `/api/v1/health/live` endpoints extracting live OS resource metrics via `psutil`.
- [x] **Automated Pytest Suite:** 100% passing unit and integration tests (`test_health.py`).
- [x] **Frontend SRE Console:** High-aesthetic dark-mode observability dashboard built with React, TypeScript, and Vite.
- [x] **Node Collector Probe Skeleton:** Standalone agent probe daemon in [`agents/node_collector/`](agents/node_collector/).
- [x] **Automated CI/CD:** GitHub Actions workflow in [`.github/workflows/ci.yml`](.github/workflows/ci.yml).

---

## 🛠️ Quickstart Guide

### 1. Backend Service (FastAPI)

```bash
cd backend

# Create virtual environment (Windows / Linux)
python -m venv .venv
source .venv/bin/activate   # On Windows: .\.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run automated tests
pytest -v

# Start development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
- Swagger Interactive Documentation: [http://localhost:8000/api/v1/docs](http://localhost:8000/api/v1/docs)
- Health Probe: [http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health)

### 2. Frontend SRE Console (Vite + React)

```bash
cd frontend

# Install packages
npm install

# Build verification
npm run build

# Start frontend dev server
npm run dev
```
- Web Console: [http://localhost:5173](http://localhost:5173)

### 3. Node Collector Agent

```bash
cd agents/node_collector
python collector.py
```

---

## 🛡️ Security & Code Quality Standards

- Strict typing with Pydantic v2 (Python) and TypeScript 5.9 (Frontend).
- Clean separation between routing, business logic, schemas, and probes.
- Zero mock secrets or committed credentials (`.env` strictly excluded in `.gitignore`).
- Unit and integration tests for every endpoint.
