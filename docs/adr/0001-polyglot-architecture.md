# ADR 0001: Selection of Polyglot Architecture for OpsPilot

## Status
Accepted

## Date
2026-10-11

## Context
OpsPilot requires a reliable, scalable, and responsive architecture capable of handling high-throughput infrastructure telemetry, low-latency WebSocket broadcasting to an operations console, and integration with modern AI/LLM models for root cause analysis.

We evaluated monolithic frameworks (e.g., standard Django, Ruby on Rails) vs. a polyglot decoupled micro-modular architecture.

## Decision
We decided to adopt a decoupled architecture:
1. **Backend:** Python with **FastAPI** (`asyncio`).
   - *Rationale:* High async performance matching Node.js/Go for I/O operations, native integration with AI/ML ecosystems (PyTorch, LangChain, ChromaDB, Hugging Face), automatic OpenAPI (Swagger) generation, and robust schema validation via Pydantic v2.
2. **Frontend:** **React + TypeScript + Vite**.
   - *Rationale:* Fast development cycle, static typing for complex telemetry state management, predictable rendering of high-frequency data streams, and rich charting ecosystem.
3. **Agent Probes:** Lightweight Python daemon utilizing `psutil`.
   - *Rationale:* Cross-platform compatibility (Linux, Windows, macOS), minimal memory footprint, and low CPU overhead.
4. **Primary Storage & Caching:** **PostgreSQL + Redis**.
   - *Rationale:* ACID guarantees for users, incidents, and audit trails in PostgreSQL; sub-millisecond TTL caching for live telemetry heartbeats and rate limiting in Redis.

## Consequences
- **Positive:** Maximum performance where needed; native AI readiness without external language bridges; independent frontend and backend scaling; clear separation of concerns.
- **Negative:** Requires managing separate development runtimes (Python virtualenv and Node/npm) and maintaining strict API contracts.
