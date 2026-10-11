# OpsPilot 3-Month Development Roadmap (15 Sprints)

This roadmap maps out the 3-month development cycle across **15 distinct sprints (5–6 days per sprint)**, designed specifically for continuous GitHub evaluation and incremental, verifiable progress.

---

## Sprint Schedule Overview

| Sprint | Days | Focus Area | Key Deliverable | GitHub Milestone Tag |
|---|---|---|---|---|
| **Sprint 1** | Days 1–5 | Architecture & Foundation | Polyglot skeleton, CI/CD, docs, health endpoint, console shell | `v0.1.0-alpha.1` |
| **Sprint 2** | Days 6–10 | Database Modeling & Auth | PostgreSQL schemas, JWT auth, RBAC middleware, unit tests | `v0.1.0-alpha.2` |
| **Sprint 3** | Days 11–15 | Telemetry Ingestion API | Agent ingestion endpoint, heartbeat tracking, mock probes | `v0.2.0-beta.1` |
| **Sprint 4** | Days 16–20 | Real-Time Engine & WebSockets | Live WebSocket bus, alert threshold engine, status cards UI | `v0.2.0-beta.2` |
| **Sprint 5** | Days 21–25 | Working MVP Review | Full ingestion-to-dashboard pipeline, end-to-end tests | `v0.3.0-mvp` |
| **Sprint 6** | Days 26–30 | Log Ingestion & Indexing | Syslog/Docker log stream parser, Timescale/Redis caching | `v0.4.0-alpha.1` |
| **Sprint 7** | Days 31–35 | AI Diagnosis & RAG Core | LLM Root Cause Analysis, ChromaDB runbook embeddings | `v0.5.0-beta.1` |
| **Sprint 8** | Days 36–40 | Runbook Automation Pipeline | Step-by-step executor, approval gates, command sandbox | `v0.6.0-beta.1` |
| **Sprint 9** | Days 41–45 | Container & Host Daemon | Real Python/psutil agent probe, container log tailing | `v0.7.0-beta.1` |
| **Sprint 10** | Days 46–50 | Production Core Integration | AI + Incident + Auto-Remediation unified workflow | `v0.8.0-rc.1` |
| **Sprint 11** | Days 51–55 | Cost & Health Optimization | Idle node detector, resource waste analytics, PDF reports | `v0.9.0-rc.1` |
| **Sprint 12** | Days 56–60 | Security & Audit Hardening | Immutable audit logging, rate limiting, Snyk vulnerability scan | `v0.9.5-rc.2` |
| **Sprint 13** | Days 61–65 | Stress & Chaos Testing | Locust load tests, network latency & failure simulations | `v0.9.8-rc.3` |
| **Sprint 14** | Days 66–70 | Dockerization & Deployment | Multi-container Docker Compose, live cloud deployment | `v1.0.0-gold` |
| **Sprint 15** | Days 71–75+ | Defense Prep & Portfolio Evidence | Viva interview questions, architecture defense, demo video | `v1.0.0-final` |

---

## Definition of Done (DoD) for Each Sprint

A sprint is considered **Done** only when:
1. All planned code features compile, run, and pass automated unit/integration tests.
2. Code adheres to clean architecture (separation of concerns, typing, error handling).
3. Documentation (README, API docs, ADRs) is updated to reflect all changes.
4. Git commits follow conventional commits (`feat:`, `fix:`, `docs:`, `test:`, `refactor:`).
5. A detailed Sprint Summary is compiled for professor review.
