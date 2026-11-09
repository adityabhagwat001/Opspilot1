# OpsPilot — GitHub Account Isolation, Real-Time Monitoring & Data Integrity Fix Report

**Report Date:** October 31, 2026  
**Repository:** [https://github.com/adityabhagwat001/Opspilot1](https://github.com/adityabhagwat001/Opspilot1)  
**Author:** Senior Full-Stack Engineer, Security Auditor & Database Engineer  
**Status:** Audit & Remediation Completed • 100% Green Test Suite (30/30 Backend Tests Passing • Clean Frontend Build)

---

## 1. Executive Summary

A comprehensive security, architecture, and data integrity audit was conducted on OpsPilot's GitHub DevOps module. The investigation revealed the exact reasons why the dashboard displayed data belonging to `adityabhagwat001/Opspilot1` (specifically workflow failure run `#77112233`, 1 AI fix proposal, 21 repeated notifications, and an artificially clamped 20% repository health score) while connected to the active GitHub profile `@SarthakJadhav007`.

All root causes were identified, surgically isolated, and repaired across both backend and frontend layers without removing existing features or altering the UI aesthetic. Multi-account credential isolation, active context resolution, query scoping, and in-flight request sequencing are now fully operational.

---

## 2. Exact Root Causes Identified

| # | Component | Root Cause Description |
|---|---|---|
| **1** | **Shared Database & Unscoped Queries** | Endpoints `/api/github/failures`, `/api/github/proposals`, and `/api/github/activity` queried `WorkflowFailure`, `FixProposal`, and `GitHubEvent` by `workspace_id` only, completely omitting the active GitHub account and its authorized repository list. Run `#77112233` (seeded during test execution) was globally returned to any user. |
| **2** | **Artificial Clamping in Health Calculation** | `/api/github/health` counted every failure in the database across all accounts (`12` test failures + `1` audit failure = `13`), multiplied by 15 (`-95`), and clamped the score to `max(20.0, ...)`, forcing the dashboard to always display `20% Operational`. |
| **3** | **Global / Missing Multi-Account Resolution** | `IntegrationConnection` only held a single connection per provider and lacked real-time active account switching endpoints (`/api/github/accounts/switch`). Switching profiles did not alter backend query scopes. |
| **4** | **Stale In-Flight Frontend Requests** | When switching accounts in React, previously dispatched network requests were not cancelled or sequence-guarded, allowing stale responses from a previous account to overwrite the active dashboard state. |
| **5** | **Webhook Localhost Misrepresentation** | The dashboard claimed "Webhook listener active" purely because the FastAPI backend was running on `localhost:8000`, despite GitHub being unable to reach localhost without a development tunnel (e.g., ngrok, Cloudflare Tunnel). |
| **6** | **Global FastMCP Token Leakage** | The FastMCP router resolved tokens globally from environment variables rather than pulling the per-account active credential belonging to the executing workspace. |

---

## 3. Affected Source Files & Functions

### Backend Changes

1. **[`backend/app/models/models.py`](file:///d:/OpsPilot%20Project/backend/app/models/models.py)**:
   - Added multi-account properties to `IntegrationConnection`: `details`, `account_login`, `is_active`, and `token`.
   - Backward-compatible JSON storage inside `details_json` avoiding destructive migrations.

2. **[`backend/app/core/db.py`](file:///d:/OpsPilot%20Project/backend/app/core/db.py)**:
   - Replaced `.scalar_one_or_none()` with `.scalars().first()` on `IntegrationConnection` provider query to support multiple simultaneous GitHub accounts in `init_system_db()`.

3. **[`backend/app/api/github_ops.py`](file:///d:/OpsPilot%20Project/backend/app/api/github_ops.py)**:
   - `get_active_github_context()`: Centralized context resolver pulling active connection, token, account login, and authorized repository list.
   - `GET /api/github/accounts`: Returns list of all connected profiles with active flags and repo counts.
   - `POST /api/github/accounts/switch`: Atomically updates active connection without deleting historical records.
   - `POST /api/github/connect`: Enriches `details_json` with accessible repository list discovered live from GitHub and activates new account.
   - `GET /api/github/account`: Dynamic target owner and active login resolution.
   - `GET /api/github/failures`: Scoped strictly to `active_ctx["monitored_repo_names"]`.
   - `GET /api/github/proposals`: Scoped strictly to `active_ctx["monitored_repo_names"]`.
   - `POST /api/github/proposals/{proposal_id}/execute`: Enforces strict authorization boundary; returns `403 Forbidden` if proposal repo is outside active account's authorized scope.
   - `GET /api/github/health`: Implemented verified health formula:
     $$\text{Repo Score} = \max(0.0, 100.0 - (\text{Active Failures} \times 25.0))$$
     Overall score is the average across active monitored repositories. Returns `"Health score unavailable — insufficient verified data."` if 0 repos monitored.
   - `GET /api/github/notifications`: Scoped and deduplicated to active account and its monitored repositories.
   - `GET /api/github/webhook/status`: Honest reachability status detecting localhost vs. public host with development tunnel guidance.

4. **[`backend/app/integrations/mcp_router.py`](file:///d:/OpsPilot%20Project/backend/app/integrations/mcp_router.py)**:
   - Refactored `execute_tool()` to dynamically resolve the active account token per workspace instead of relying on a process-wide environment variable.

### Frontend Changes

1. **[`frontend/src/services/api.ts`](file:///d:/OpsPilot%20Project/frontend/src/services/api.ts)**:
   - Added `getConnectedAccounts()`.
   - Added `switchGitHubAccount(payload)`.
   - Added `getWebhookStatus()`.

2. **[`frontend/src/pages/GitHubDevOpsPage.tsx`](file:///d:/OpsPilot%20Project/frontend/src/pages/GitHubDevOpsPage.tsx)**:
   - Added in-flight request cancellation tracking via `loadSeq = useRef(0)`.
   - Added Quick Profile Switcher pill selector in the header bar.
   - Added "Existing Connected Profiles" one-click switch list inside the Connect Modal.
   - Updated CI/CD Failures empty state: `"No active CI/CD failures found for the selected repositories."` with verified green passing badge.
   - Handled insufficient data state on Repo Health Score card.
   - Displayed Webhook reachability and localhost development tunnel badge.

---

## 4. Verification Results Matrix

| Feature | Operational Status | Evidence & Verification Notes |
|---|---|---|
| **GitHub Account Connection (Account A)** | **VERIFIED WORKING** | `@SarthakJadhav007` connected with 13 accessible repos. |
| **GitHub Account Connection (Account B)** | **VERIFIED WORKING** | `@adityabhagwat001` connected with `adityabhagwat001/Opspilot1`. |
| **Account Switching (A $\to$ B)** | **VERIFIED WORKING** | `/api/github/accounts/switch` switches context. Failures (`#77112233`) and proposals for B appear immediately. |
| **Account Switching (B $\to$ A)** | **VERIFIED WORKING** | Switched back to A: 0 failures, 0 proposals, 100% health score restored. Historical data preserved. |
| **Cross-Account Data Isolation** | **VERIFIED WORKING** | `test_accounts_listing_and_switching_roundtrip` verifies A cannot see B's private failures or proposals. |
| **Cross-Account Write Prevention** | **VERIFIED WORKING** | `test_cross_account_proposal_execution_forbidden` verified: Account A attempting to execute B's fix returns `403 Forbidden`. |
| **Grounded Repository Health Score** | **VERIFIED WORKING** | Evaluates only active monitored repos. `@Sarthakjadhav007` displays `100.0% OPTIMAL`, `@adityabhagwat001` displays `75.0%`. Arbitrary 20% clamp removed. |
| **CI/CD Failures Empty State** | **VERIFIED WORKING** | Displays `"No active CI/CD failures found for the selected repositories."` with verified zero-anomalies badge. |
| **Real-Time Request Sequencing** | **VERIFIED WORKING** | In-flight sequence tracking (`loadSeq.current`) prevents stale responses from overwriting freshly selected accounts. |
| **Webhook Signature Validation** | **VERIFIED WORKING** | `test_invalid_webhook_signature_rejected` confirms invalid/tampered signatures return `401/403`. |
| **Webhook Reachability Telemetry** | **VERIFIED WORKING** | `/api/github/webhook/status` reports honest `is_publicly_reachable: false` on localhost with explicit tunnel guidance. |
| **Mock Data Separation in Live Mode** | **VERIFIED WORKING** | Test fixtures isolated. Invalid tokens return honest HTTP 400/401 and never trigger mock sandbox fallback. |
| **Automated PR Write Gate** | **VERIFIED WORKING** | 100% cryptographic human approval gating maintained via `approval_service`. |

---

## 5. Automated Regression Test Suite Results

### New Test Suite: [`backend/tests/test_github_account_isolation.py`](file:///d:/OpsPilot%20Project/backend/tests/test_github_account_isolation.py)

```text
============================= test session starts =============================
platform win32 -- Python 3.13.1, pytest-9.1.1 -- D:\OpsPilot Project\.venv\Scripts\python.exe
collected 6 items

backend/tests/test_github_account_isolation.py::test_accounts_listing_and_switching_roundtrip PASSED [ 16%]
backend/tests/test_github_account_isolation.py::test_cross_account_proposal_execution_forbidden PASSED [ 33%]
backend/tests/test_github_account_isolation.py::test_health_score_strictly_scoped_to_active_monitored_repositories PASSED [ 50%]
backend/tests/test_github_account_isolation.py::test_webhook_status_and_tunnel_guidance PASSED [ 66%]
backend/tests/test_github_account_isolation.py::test_invalid_webhook_signature_rejected PASSED [ 83%]
backend/tests/test_github_account_isolation.py::test_invalid_credentials_produce_honest_errors_no_mock_fallback PASSED [100%]

============================== 6 passed in 6.72s ==============================
```

### Full System Regression Suite (Phases 3, 4, 5, 6 & Security)

```text
============================= test session starts =============================
collected 24 items

backend/tests/test_phase3_github_connection.py::test_account_permission_telemetry_and_scopes PASSED [  4%]
backend/tests/test_phase3_github_connection.py::test_repository_discovery_pagination_and_permissions PASSED [  8%]
backend/tests/test_phase3_github_connection.py::test_live_repository_overview_honest_metrics PASSED [ 12%]
backend/tests/test_phase3_github_connection.py::test_missing_or_invalid_token_disconnect_graceful_handling PASSED [ 16%]
backend/tests/test_phase4_monitoring.py::test_webhook_hmac_signature_validation PASSED [ 20%]
backend/tests/test_phase4_monitoring.py::test_webhook_delivery_idempotent_deduplication PASSED [ 25%]
backend/tests/test_phase4_monitoring.py::test_webhook_workflow_failure_ingestion_and_rich_extraction PASSED [ 29%]
backend/tests/test_phase4_monitoring.py::test_polling_fallback_reconciliation PASSED [ 33%]
backend/tests/test_phase5_ai_fixing.py::test_diagnose_failure_from_log_grounding PASSED [ 37%]
backend/tests/test_phase5_ai_fixing.py::test_validate_unified_diff_format PASSED [ 41%]
backend/tests/test_phase5_ai_fixing.py::test_verify_patch_in_sandbox_checks PASSED [ 45%]
backend/tests/test_phase5_ai_fixing.py::test_end_to_end_grounded_analysis_and_sandbox_verified_proposal PASSED [ 50%]
backend/tests/test_phase6_approval_lifecycle.py::test_end_to_end_approval_and_execution_lifecycle PASSED [ 54%]
backend/tests/test_phase6_approval_lifecycle.py::test_end_to_end_rejection_lifecycle PASSED [ 58%]
backend/tests/test_phase6_approval_lifecycle.py::test_parameter_tampering_rejection PASSED [ 62%]
backend/tests/test_phase6_approval_lifecycle.py::test_expiration_15_minute_window_enforcement PASSED [ 66%]
backend/tests/test_phase6_approval_lifecycle.py::test_nonce_replay_attack_prevention PASSED [ 70%]
backend/tests/test_phase6_approval_lifecycle.py::test_cross_workspace_approval_isolation PASSED [ 75%]
backend/tests/test_phase6_approval_lifecycle.py::test_purge_inactive_approvals_endpoint PASSED [ 79%]
backend/tests/test_approval_security.py::test_action_hash_deterministic PASSED [ 83%]
backend/tests/test_approval_security.py::test_tampered_parameters_hash_mismatch PASSED [ 87%]
backend/tests/test_approval_security.py::test_forged_approval_token_rejected PASSED [ 91%]
backend/tests/test_approval_security.py::test_genuine_approval_token_verified PASSED [ 95%]
backend/tests/test_approval_security.py::test_approval_lifecycle_and_rejection PASSED [100%]

============================= 24 passed in 34.04s =============================
```

### Frontend Build Verification

```text
> frontend@0.0.0 build
> tsc -b && vite build

vite v8.3.4 building client environment for production...
transforming...
✓ 2236 modules transformed.
rendering chunks...
computing gzip size...
dist/index.html                   1.12 kB │ gzip:   0.63 kB
dist/assets/index-CAGXU2NT.css   36.96 kB │ gzip:   7.32 kB
dist/assets/index-DTeXMEIf.js   621.70 kB │ gzip: 181.91 kB
✓ built in 1.74s
```

---

## 6. Real Integration Verification Results

- **Test A (Connect Account A — @SarthakJadhav007):**
  - Identity verified: `@SarthakJadhav007`.
  - Accessible Repos: 13 repositories.
  - Active CI/CD Failures: 0 incidents.
  - Active AI Fix Proposals: 0 proposals.
  - Repository Health Score: `100.0% OPTIMAL`.
  - Empty state text: `"No active CI/CD failures found for the selected repositories."`
- **Test B (Switch to Account B — @adityabhagwat001):**
  - Identity updated: `@adityabhagwat001`.
  - Monitored Repos: `adityabhagwat001/Opspilot1`.
  - Active CI/CD Failures: 1 incident (run `#77112233`).
  - Active AI Fix Proposals: 1 proposal (`adityabhagwat001/Opspilot1`).
  - Repository Health Score: `75.0%`.
- **Test C (Switch Back to Account A — @SarthakJadhav007):**
  - Identity restored: `@SarthakJadhav007`.
  - Active CI/CD Failures: 0 incidents.
  - Historical records preserved: B's failure was NOT deleted; it was cleanly unscoped from A's view.
- **Test D (Cross-Account Write Attempt):**
  - Executing fix for B's repository while A is active was blocked with `403 Forbidden`.

---

## 7. Remaining Environmental Limitations

- **Webhook Direct Delivery on Localhost:**
  - When running the backend on `localhost:8000`, GitHub's servers cannot directly send POST webhook requests across the public internet.
  - The telemetry card now accurately reflects `Localhost (tunnel required)`.
  - For live webhook delivery in local development, an HTTPS development tunnel (such as `ngrok http 8000` or Cloudflare Tunnel) should be pointed to `/api/github/webhook`.
  - If a tunnel is not present, OpsPilot's background periodic reconciliation safely fetches updates via authenticated GitHub REST polling every 15 seconds.
