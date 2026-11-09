# OpsPilot Complete Role-Based Access Control (RBAC) & Enterprise Security Report

**Document Status:** Complete & Verified  
**Date:** November 2026  
**Audience:** Enterprise Security, Platform Engineering, DevOps Leadership  
**Project:** OpsPilot — Agentic AI-Powered Enterprise Operations Assistant  
**Repository:** https://github.com/adityabhagwat001/Opspilot1  

---

## Executive Summary

OpsPilot previously provided two login personas—**Lead DevOps Operator** (`operator`) and **Enterprise Administrator** (`admin`). However, both roles possessed near-identical backend privileges and UI capabilities: operators could approve or reject write actions, execute code modifications directly to remote repositories, switch and configure integrations, delete workflows and proposals, and inspect enterprise-wide audit logs.

This implementation establishes an end-to-end, defense-in-depth Role-Based Access Control (RBAC) architecture. The **Lead DevOps Operator** is strictly scoped to investigation, AI diagnostics, log analysis, and proposing fixes for review. The **Enterprise Administrator** retains sole authority to review, approve/reject high-risk operations, configure integration secrets, and monitor platform-wide activity.

All 99 automated test cases across the full backend suite (including 16 dedicated RBAC and security isolation tests) pass with 100% compliance, and the React/TypeScript frontend compiles cleanly with zero errors.

---

## 1. Original RBAC Problems Found

1. **Permissive Route Dependencies in Approval Center:**  
   The FastAPI approval endpoints (`POST /api/approvals/{id}/approve`, `POST /api/approvals/{id}/reject`, `DELETE /api/approvals/{id}`, and `POST /api/approvals/purge`) permitted both `admin` and `operator` roles through `require_role(["admin", "operator"])`.
2. **Operator Execution of GitHub Mutations:**  
   The endpoint `POST /api/github/proposals/{proposal_id}/execute` allowed operators to push code patches and create remote GitHub pull requests without administrator intervention.
3. **Unrestricted Integration Management:**  
   Endpoints for connecting GitHub accounts, switching active profiles, toggling repository monitoring, and disconnecting accounts accepted operators.
4. **Destructive Operations by Operators:**  
   Endpoints for dismissing workflow failures (`DELETE /api/github/failures/{id}`) and deleting proposals (`DELETE /api/github/proposals/{id}`) were accessible to operators.
5. **No Centralized Permission Registry:**  
   Access checks relied on scattered ad-hoc string comparisons rather than a formal, auditable permission matrix.
6. **No Separation of Duties Enforcement:**  
   Approval routines permitted the same user who authored or requested a proposal to approve and execute it.
7. **Unscoped Audit Log Visibility:**  
   Operators could view enterprise-wide audit records and solutions from all users across the organization.
8. **UI Inconsistencies:**  
   The React frontend rendered active "Approve & Execute" and "Reject Action" buttons for operators, inviting unauthorized actions that should have been restricted to administrators.

---

## 2. Exact Root Causes

| Component | Root Cause |
|---|---|
| `backend/app/api/approvals.py` | Routes were decorated with `Depends(require_role(["admin", "operator"]))`, conflating diagnostic and administrative responsibilities. |
| `backend/app/api/github_ops.py` | Execution and integration mutation routes accepted `["admin", "operator"]` instead of enforcing admin-only access. |
| `backend/app/approvals/approval_service.py` | `approve_and_execute` validated cryptographic tokens and expiry but never verified that `approver_user_id` held the `admin` role or differed from `requesting_user_id`. |
| `backend/app/api/audit.py` | Query filters lacked user-level scoping for non-admin callers. |
| `frontend/src/components/ApprovalCard.tsx` | Component did not inspect user role or permissions, rendering action buttons unconditionally. |
| Missing Permission Architecture | Lack of a centralized permission dictionary meant route security was defined haphazardly per endpoint. |

---

## 3. Files Modified & Added

### Backend Architecture
- **`backend/app/core/permissions.py` (Added):** Central registry defining granular string constants and the `ROLE_PERMISSIONS` dictionary for `operator` and `admin`.
- **`backend/app/auth/deps.py` (Modified):** Added `require_permission(permission: str)` dependency and refined `require_role`.
- **`backend/app/api/auth.py` (Modified):** Injected assigned `permissions` array into `/login` and `/me` responses.
- **`backend/app/api/approvals.py` (Modified):** Restricted `approve` and `purge` to `admin`; scoped `reject` so operators can only cancel their own submissions while admins can reject any request; added `Header` import for optional Separation of Duties enforcement.
- **`backend/app/api/github_ops.py` (Modified):** Restricted `/proposals/{id}/execute`, `/connect`, `/disconnect`, `/accounts/switch`, `/repositories/monitor`, and deletion routes to `admin`.
- **`backend/app/approvals/approval_service.py` (Modified):** Added approver role validation (`admin` required) and optional Separation of Duties checking (`approver != requester`).
- **`backend/app/api/audit.py` (Modified):** Enforced user scoping (`AuditLog.user_id == user.id`) for operators in audit history and solution inspection.
- **`backend/app/agents/agent_graph.py` & `backend/app/api/chat.py` (Modified):** Passed authenticated `user_role` into LangGraph `OpsAgentState` and chat execution context.

### Frontend Role-Aware UI
- **`frontend/src/types/index.ts` (Modified):** Added `permissions?: string[]` to `User` interface.
- **`frontend/src/components/Navbar.tsx` (Modified):** Added visual role badges displaying `Enterprise Admin` (Amber/Shield) or `Lead DevOps Operator` (Cyan/Terminal).
- **`frontend/src/components/ApprovalCard.tsx` (Modified):** Replaced execution buttons with an informative read-only banner for Operators explaining that administrator privileges are required.
- **`frontend/src/pages/ApprovalsPage.tsx` (Modified):** Passed `userRole` to cards and hid the administrative "Purge Inactive" button for operators.
- **`frontend/src/pages/GitHubDevOpsPage.tsx` (Modified):** Hidden "Switch Profile", "Connect Profile", "Execute Proposal", and dismissal actions for operators; added role status notices.
- **`frontend/src/pages/IntegrationsPage.tsx` (Modified):** Added read-only Operator view banner and disabled credential editing.
- **`frontend/src/pages/AuditPage.tsx` (Modified):** Added scope indicator ("Enterprise-Wide Scope" vs "Operator Activity Scope").
- **`frontend/src/App.tsx` (Modified):** Supplied `currentUser={user}` across all routes.

### Verification Suite
- **`backend/tests/test_complete_enterprise_rbac.py` (Added):** 16 comprehensive automated tests verifying all operator limits, admin privileges, separation of duties, MCP tool execution restrictions, and prompt injection defense.

---

## 4. Central Permission Matrix

| Permission Identifier | Operator | Administrator | Purpose |
|---|:---:|:---:|---|
| `dashboard:read` | Allow | Allow | View operations dashboard & summary metrics |
| `ai:chat` | Allow | Allow | Interact with OpsPilot AI Assistant |
| `ai:analyze` | Allow | Allow | Trigger grounded failure log analysis |
| `github:read` | Allow | Allow | View repositories, workflow runs, failure logs |
| `github:propose_fix` | Allow | Allow | Generate AI code fix & run sandbox verification |
| `github:execute_approved_fix` | **Deny** | Allow | Push code patch to remote branch & open PR |
| `github:manage_integrations` | **Deny** | Allow | Connect/disconnect accounts, switch active profile |
| `database:read` | Allow | Allow | Inspect schemas and run read-only queries |
| `database:propose_write` | Allow | Allow | Propose schema/data changes for human approval |
| `database:execute_approved_write` | **Deny** | Allow | Execute approved SQL mutations |
| `approval:create` | Allow | Allow | Register new change proposal in Approval Center |
| `approval:read` | Allow | Allow | Inspect pending, approved, and rejected requests |
| `approval:approve` | **Deny** | Allow | Authorize and trigger high-risk write execution |
| `approval:reject` | Own Only | Allow | Cancel own proposal (operator) / Reject any (admin) |
| `audit:read_own` | Allow | Allow | Read audit events initiated by current user |
| `audit:read_all` | **Deny** | Allow | Read enterprise-wide audit records across all users |
| `integration:read` | Allow | Allow | View connected integration health and status |
| `integration:manage` | **Deny** | Allow | Rotate keys, edit secrets, configure webhooks |
| `users:manage` | **Deny** | Allow | Manage workspace members and role assignments |
| `settings:manage` | **Deny** | Allow | Modify system-wide operational policies |
| `system:health_read` | Limited | Full | Monitor container, broker, and worker health |

---

## 5. Authentication & Session Security

- **Tamper-Proof Role Resolution:** Roles are retrieved strictly from the database user record (`User.role`) during authentication and encoded into the cryptographically signed JWT `sub` and claims.
- **Backend Source of Truth:** Role claims supplied by clients or modified via developer tools are ignored. All authorization decisions use `Depends(get_current_user)` or `Depends(require_role)`.
- **Exposed User Context:** The `/api/auth/me` and `/api/auth/login` endpoints return safe user profiles accompanied by the evaluated `permissions` list based on `ROLE_PERMISSIONS`.

---

## 6. Operator Role Boundaries

### Allowed Actions
1. Log in to OpsPilot dashboard.
2. View operational metrics and GitHub repository status.
3. Monitor GitHub Actions CI/CD workflow failures.
4. Retrieve and inspect error logs.
5. Click "Analyze with AI" and query the AI Assistant.
6. Inspect database schemas and execute read-only SQL queries.
7. Generate AI fix proposals with isolated scratch/sandbox verification.
8. Submit proposed code fixes to the Approval Center.
9. Track status of submitted approval requests.
10. Cancel/withdraw their own pending approval requests.
11. View personal audit log history (`user_id == current_user.id`).

### Forbidden Actions (Enforced with HTTP 403 Forbidden)
1. Cannot approve any change proposal (`POST /api/approvals/{id}/approve` returns 403).
2. Cannot reject requests as an administrator (`POST /api/approvals/{id}/reject` returns 403 on non-owned requests).
3. Cannot purge approval history (`POST /api/approvals/purge` returns 403).
4. Cannot execute proposals (`POST /api/github/proposals/{id}/execute` returns 403).
5. Cannot connect, disconnect, or switch GitHub integration profiles (returns 403).
6. Cannot dismiss workflow failures or delete proposals (returns 403).
7. Cannot view enterprise-wide audit logs from other users.
8. Cannot execute write operations through MCP servers or AI prompt manipulation.

---

## 7. Administrator Role Capabilities & Safeguards

### Allowed Actions
1. All diagnostic, analysis, and AI consultation capabilities.
2. Access the Approval Center to inspect proposed diffs and sandbox test results.
3. Approve and execute authorized change requests.
4. Reject any change request with reason logging.
5. Purge and prune historical approval records.
6. Manage GitHub and PostgreSQL enterprise integrations.
7. Switch active integration profiles and monitor/unmonitor repositories.
8. View enterprise-wide audit history across all workspace operators.

### Safeguards Imposed on Administrators
1. Plaintext passwords are never returned or stored (Argon2 / bcrypt hashing).
2. Integration tokens and API secrets are masked in responses (`ghp_****`).
3. Replay protection: Approval tokens can only be consumed once (`ConsumedApprovalToken` verification).
4. Expired approval signatures are automatically rejected.
5. Separation of Duties: When enforced via policy or `X-Enforce-Separation-Of-Duties`, administrators cannot approve change requests they submitted themselves.

---

## 8. LangGraph & FastMCP Security Boundaries

1. **Context-Aware Role Propagation:** The authenticated `user_role` is passed into `OpsAgentState` upon each conversation turn.
2. **Deterministic MCP Tool Gating:**
   - FastMCP tools (`apply_github_fix`, `drop_database_table`, `alter_database_schema`, `execute_raw_mutation`) enforce pre-flight approval validation.
   - Without an active, cryptographically signed approval token, write tools return an `APPROVAL_REQUIRED` status and pause execution.
3. **Prompt Injection Resilience:**
   - AI instructions instructing the agent to "ignore rules", "grant admin permissions", or "execute fix directly" cannot override backend route decorators or database-level constraints.
   - MCP write tools reject unapproved execution regardless of system prompts.

---

## 9. Test Suite Verification Results

The entire backend test suite was executed in the project virtual environment (`.\.venv\Scripts\python -m pytest backend/tests`):

```text
collected 99 items

backend\tests\test_ai_issue_resolution_workflow.py ......                [  6%]
backend\tests\test_approval_security.py .....                            [ 11%]
backend\tests\test_complete_enterprise_rbac.py ................          [ 27%]
backend\tests\test_github_account_isolation.py ......                    [ 33%]
backend\tests\test_github_intelligence.py ......                         [ 39%]
backend\tests\test_langgraph_agent.py ........                           [ 47%]
backend\tests\test_mcp_servers.py .............                          [ 60%]
backend\tests\test_phase3_github_connection.py ....                      [ 64%]
backend\tests\test_phase4_monitoring.py ....                             [ 68%]
backend\tests\test_phase5_ai_fixing.py ....                              [ 72%]
backend\tests\test_phase6_approval_lifecycle.py .......                  [ 79%]
backend\tests\test_phase7_postgres_read_only.py .........                [ 88%]
backend\tests\test_pr_status_verification.py .....                       [ 93%]
backend\tests\test_rbac_and_replay_boundary.py ......                    [100%]

============================== 99 passed in 146.34s ==============================
```

### Breakdown of Dedicated RBAC Tests (`test_complete_enterprise_rbac.py`)
1. `test_operator_can_view_dashboard_and_failures`: PASSED
2. `test_operator_can_analyze_failure_with_ai`: PASSED
3. `test_operator_can_propose_fix`: PASSED
4. `test_operator_cannot_approve_request`: PASSED (403 Forbidden verified)
5. `test_operator_cannot_execute_proposal_directly`: PASSED (403 Forbidden verified)
6. `test_operator_cannot_reject_request_as_admin`: PASSED (403 Forbidden verified)
7. `test_operator_can_cancel_own_request`: PASSED
8. `test_operator_cannot_manage_github_integrations`: PASSED (403 Forbidden on switch, connect, disconnect)
9. `test_operator_cannot_delete_failures_or_proposals`: PASSED (403 Forbidden verified)
10. `test_operator_cannot_purge_approvals`: PASSED (403 Forbidden verified)
11. `test_admin_can_approve_and_execute_proposal`: PASSED
12. `test_admin_can_reject_proposal`: PASSED
13. `test_admin_can_purge_approvals`: PASSED
14. `test_separation_of_duties_prevents_self_approval`: PASSED (400 Bad Request / SOD violation verified)
15. `test_mcp_write_tool_blocked_without_valid_approval`: PASSED
16. `test_prompt_injection_cannot_bypass_rbac_or_approval_gate`: PASSED

### Frontend Build Verification
Ran `npm --prefix frontend run build`:
```text
> frontend@0.0.0 build
> tsc -b && vite build

vite v8.3.4 building client environment for production...
transforming...
✓ 2238 modules transformed.
rendering chunks...
dist/index.html                   1.12 kB │ gzip:   0.63 kB
dist/assets/index-CpPcAHPK.css   39.75 kB │ gzip:   7.74 kB
dist/assets/index-DoHwQRT8.js   660.28 kB │ gzip: 188.99 kB
✓ built in 1.67s
```

---

## 10. Operational Guidelines

### How to Run the Application Locally

1. **Start the FastAPI Backend:**
   ```powershell
   $env:PYTHONPATH="backend;."
   .\.venv\Scripts\uvicorn.exe app.main:app --host 127.0.0.1 --port 8000 --reload --app-dir backend
   ```

2. **Start the React Frontend:**
   ```powershell
   npm --prefix frontend run dev
   ```

3. **Log in with Credentials:**
   - **Enterprise Administrator:** `admin@opspilot.internal` / `AdminPass123!`
   - **Lead DevOps Operator:** `operator@opspilot.internal` / `OperatorPass123!`

---

## 11. Remaining Security Considerations & Roadmap

1. **Hardware Security Module (HSM) / KMS Key Storage:** For production cloud deployment, migrate cryptographic signing keys (`JWT_SECRET`, HMAC keys) from environment variables to AWS KMS, GCP Cloud KMS, or HashiCorp Vault.
2. **Webhook Cryptographic Signature Verification:** Ensure GitHub webhook deliveries require `X-Hub-Signature-256` matching when internet ingress is opened.
3. **Multi-Factor Authentication (MFA):** Add TOTP / WebAuthn for Administrator logins prior to approving Tier 3 high-risk infrastructure write operations.

