"""
OpsPilot Custom FastMCP Server: GitHub API Integration.
Connects to official GitHub REST API (v3) using httpx.AsyncClient.
Enforces strict human approval before any write operation (issue creation, updating, commenting).
Returns standardized, typed envelopes for all tools.
"""

import os
import sys
import hmac
import hashlib
import json
import datetime
from typing import Optional, Dict, Any, List
import httpx
from fastmcp import FastMCP
from dotenv import load_dotenv

load_dotenv()


# Add parent directory to path so imports work seamlessly
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from envelope import create_success_envelope, create_error_envelope

# Initialize FastMCP Server
mcp = FastMCP("opspilot-github-server")

GITHUB_API_BASE = "https://api.github.com"
APPROVAL_SECRET = os.getenv("OPSPILOT_APPROVAL_SECRET", "opspilot_trusted_approval_boundary_secret_key_32chars")

def is_mock_allowed() -> bool:
    return os.getenv("DEMO_MODE", "false").lower() in ("true", "1", "yes") or os.getenv("MOCK_MODE", "false").lower() in ("true", "1", "yes")

def get_github_client(token: Optional[str] = None) -> httpx.AsyncClient:
    api_token = token or os.getenv("GITHUB_TOKEN", "")
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "OpsPilot-Enterprise-Agent/1.0"
    }
    if api_token:
        headers["Authorization"] = f"Bearer {api_token}"
    return httpx.AsyncClient(base_url=GITHUB_API_BASE, headers=headers, timeout=20.0)

def compute_action_hash(tool_name: str, arguments: Dict[str, Any]) -> str:
    clean_args = {k: v for k, v in arguments.items() if k not in ("approval_token", "workspace_id")}
    canonical = f"{tool_name}:{json.dumps(clean_args, sort_keys=True)}"
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

def verify_approval_token(
    tool_name: str,
    args: Dict[str, Any],
    approval_token: str,
    workspace_id: str = "default-ops"
) -> bool:
    """
    Verifies that the approval token was cryptographically signed by the OpsPilot backend
    for this EXACT tool, workspace, and CANONICAL arguments payload.
    The LLM cannot forge this token.
    """
    if not approval_token:
        return False
    try:
        parts = approval_token.split(".")
        if len(parts) != 4:
            return False
        nonce, timestamp_str, token_action_hash, signature = parts
        
        token_time = int(timestamp_str)
        now = int(datetime.datetime.now(datetime.timezone.utc).timestamp())
        if now - token_time > 900 or token_time - now > 60:
            return False

        actual_hash = compute_action_hash(tool_name, args)
        if not hmac.compare_digest(actual_hash, token_action_hash):
            return False

        canonical = f"{tool_name}:{workspace_id}:{nonce}:{timestamp_str}:{token_action_hash}"
        expected_sig = hmac.new(
            APPROVAL_SECRET.encode("utf-8"),
            canonical.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(signature, expected_sig)
    except Exception:
        return False

# =========================================================================
# MOCK DATA FOR AIR-GAPPED / DEMO EVALUATION
# =========================================================================
MOCK_REPOS = [
    {
        "id": 10101,
        "name": "auth-service",
        "full_name": "enterprise-ops/auth-service",
        "private": True,
        "description": "Core OAuth2 & JWT enterprise authentication service",
        "html_url": "https://github.com/enterprise-ops/auth-service",
        "open_issues_count": 3,
        "default_branch": "main",
        "updated_at": "2026-10-13T18:00:00Z"
    },
    {
        "id": 10102,
        "name": "infrastructure",
        "full_name": "enterprise-ops/infrastructure",
        "private": True,
        "description": "Terraform and Kubernetes infrastructure manifests",
        "html_url": "https://github.com/enterprise-ops/infrastructure",
        "open_issues_count": 2,
        "default_branch": "main",
        "updated_at": "2026-10-12T14:30:00Z"
    }
]

MOCK_ISSUES = [
    {
        "number": 42,
        "title": "Auth service connection pool saturation under peak load",
        "state": "open",
        "user": "sre-bot",
        "labels": ["critical", "incident", "database"],
        "comments_count": 5,
        "created_at": "2026-10-13T10:15:00Z",
        "updated_at": "2026-10-13T11:45:00Z",
        "html_url": "https://github.com/enterprise-ops/auth-service/issues/42",
        "body_snippet": "Connection pool reached max 50/50 connections during 09:30 UTC peak. Latency spiked to 2.4s.",
        "priority_rank": "P0 - Highest Priority (Active S1 Outage correlation)"
    },
    {
        "number": 39,
        "title": "Upgrade redis-client library to v5.2 to resolve timeout leak",
        "state": "open",
        "user": "aditya-dev",
        "labels": ["high", "bug", "redis"],
        "comments_count": 2,
        "created_at": "2026-10-11T14:20:00Z",
        "updated_at": "2026-10-12T09:10:00Z",
        "html_url": "https://github.com/enterprise-ops/auth-service/issues/39",
        "body_snippet": "Memory profile shows uncollected socket descriptors on retry loop.",
        "priority_rank": "P1 - High Priority"
    },
    {
        "number": 35,
        "title": "Add OpenTelemetry trace context to outbound webhook requests",
        "state": "open",
        "user": "sarah-ops",
        "labels": ["enhancement", "observability"],
        "comments_count": 1,
        "created_at": "2026-10-08T16:00:00Z",
        "updated_at": "2026-10-09T11:00:00Z",
        "html_url": "https://github.com/enterprise-ops/auth-service/issues/35",
        "body_snippet": "Trace header injection required for full distributed traces.",
        "priority_rank": "P3 - Low Priority"
    }
]

# =========================================================================
# GITHUB READ TOOLS
# =========================================================================

@mcp.tool()
async def list_repositories(visibility: str = "all", per_page: int = 10) -> Dict[str, Any]:
    """
    List repositories accessible by the configured GitHub token or user account.
    """
    token = os.getenv("GITHUB_TOKEN", "")
    if not token:
        if is_mock_allowed():
            return create_success_envelope(
                system="github",
                tool="list_repositories",
                data={"total_returned": len(MOCK_REPOS), "repositories": MOCK_REPOS},
                source_mode="mock_sandbox",
                resource_ids_urls=[r["html_url"] for r in MOCK_REPOS]
            )
        return create_error_envelope(
            system="github",
            tool="list_repositories",
            error="GITHUB_AUTH_REQUIRED: GITHUB_TOKEN is not configured in environment.",
            error_category="UNAUTHENTICATED"
        )
    
    try:
        async with get_github_client(token) as client:
            resp = await client.get("/user/repos", params={"visibility": visibility, "per_page": per_page, "sort": "updated"})
            if resp.status_code != 200:
                return create_error_envelope(
                    system="github",
                    tool="list_repositories",
                    error=f"GitHub API error ({resp.status_code}): {resp.text}",
                    error_category="PROVIDER_ERROR"
                )
            repos = resp.json()
            cleaned = [
                {
                    "id": r.get("id"),
                    "name": r.get("name"),
                    "full_name": r.get("full_name"),
                    "private": r.get("private"),
                    "description": r.get("description"),
                    "html_url": r.get("html_url"),
                    "open_issues_count": r.get("open_issues_count"),
                    "default_branch": r.get("default_branch"),
                    "updated_at": r.get("updated_at")
                }
                for r in repos
            ]
            return create_success_envelope(
                system="github",
                tool="list_repositories",
                data={"total_returned": len(cleaned), "repositories": cleaned},
                resource_ids_urls=[r["html_url"] for r in cleaned if r.get("html_url")]
            )
    except Exception as ex:
        return create_error_envelope(
            system="github",
            tool="list_repositories",
            error=str(ex),
            error_category="PROVIDER_ERROR"
        )

@mcp.tool()
async def get_repository_details(owner: str, repo: str) -> Dict[str, Any]:
    """
    Get metadata, stars, forks, and health of a specific GitHub repository.
    """
    token = os.getenv("GITHUB_TOKEN", "")
    if not token:
        if is_mock_allowed():
            match = next((r for r in MOCK_REPOS if r["name"] == repo), MOCK_REPOS[0])
            return create_success_envelope(
                system="github",
                tool="get_repository_details",
                data=match,
                source_mode="mock_sandbox",
                resource_ids_urls=[match["html_url"]]
            )
        return create_error_envelope(
            system="github",
            tool="get_repository_details",
            error="GITHUB_AUTH_REQUIRED: GITHUB_TOKEN is not configured in environment.",
            error_category="UNAUTHENTICATED"
        )

    try:
        async with get_github_client(token) as client:
            resp = await client.get(f"/repos/{owner}/{repo}")
            if resp.status_code == 404:
                return create_error_envelope(
                    system="github",
                    tool="get_repository_details",
                    error=f"Repository '{owner}/{repo}' not found or inaccessible.",
                    error_category="NOT_FOUND"
                )
            if resp.status_code != 200:
                return create_error_envelope(
                    system="github",
                    tool="get_repository_details",
                    error=f"GitHub API error ({resp.status_code}): {resp.text}",
                    error_category="PROVIDER_ERROR"
                )
            data = resp.json()
            cleaned = {
                "full_name": data.get("full_name"),
                "description": data.get("description"),
                "html_url": data.get("html_url"),
                "stars": data.get("stargazers_count"),
                "forks": data.get("forks_count"),
                "open_issues": data.get("open_issues_count"),
                "default_branch": data.get("default_branch"),
                "language": data.get("language")
            }
            return create_success_envelope(
                system="github",
                tool="get_repository_details",
                data=cleaned,
                resource_ids_urls=[cleaned["html_url"]] if cleaned.get("html_url") else []
            )
    except Exception as ex:
        return create_error_envelope(
            system="github",
            tool="get_repository_details",
            error=str(ex),
            error_category="PROVIDER_ERROR"
        )

@mcp.tool()
async def list_issues(
    owner: str,
    repo: str,
    state: str = "open",
    labels: Optional[str] = None,
    per_page: int = 15
) -> Dict[str, Any]:
    """
    Retrieve live issues from a GitHub repository, filtered by state and labels.
    Explicitly distinguishes pull requests from actual issues.
    """
    token = os.getenv("GITHUB_TOKEN", "")
    if not token:
        if is_mock_allowed():
            return create_success_envelope(
                system="github",
                tool="list_issues",
                data={
                    "owner": owner,
                    "repo": repo,
                    "count": len(MOCK_ISSUES),
                    "issues": MOCK_ISSUES
                },
                source_mode="mock_sandbox",
                resource_ids_urls=[i["html_url"] for i in MOCK_ISSUES]
            )
        return create_error_envelope(
            system="github",
            tool="list_issues",
            error="GITHUB_AUTH_REQUIRED: GITHUB_TOKEN is not configured in environment.",
            error_category="UNAUTHENTICATED"
        )

    params = {"state": state, "per_page": per_page, "sort": "updated", "direction": "desc"}
    if labels:
        params["labels"] = labels

    try:
        async with get_github_client(token) as client:
            resp = await client.get(f"/repos/{owner}/{repo}/issues", params=params)
            if resp.status_code != 200:
                return create_error_envelope(
                    system="github",
                    tool="list_issues",
                    error=f"GitHub API error ({resp.status_code}): {resp.text}",
                    error_category="PROVIDER_ERROR"
                )
            
            raw_issues = resp.json()
            # Explicitly filter out pull requests which GitHub includes in issues endpoint
            issues = [i for i in raw_issues if "pull_request" not in i]
            cleaned = [
                {
                    "number": i.get("number"),
                    "title": i.get("title"),
                    "state": i.get("state"),
                    "user": i.get("user", {}).get("login"),
                    "labels": [l.get("name") for l in i.get("labels", [])],
                    "comments_count": i.get("comments"),
                    "created_at": i.get("created_at"),
                    "updated_at": i.get("updated_at"),
                    "html_url": i.get("html_url"),
                    "body_snippet": (i.get("body") or "")[:200]
                }
                for i in issues
            ]
            return create_success_envelope(
                system="github",
                tool="list_issues",
                data={"owner": owner, "repo": repo, "count": len(cleaned), "issues": cleaned},
                resource_ids_urls=[i["html_url"] for i in cleaned if i.get("html_url")]
            )
    except Exception as ex:
        return create_error_envelope(
            system="github",
            tool="list_issues",
            error=str(ex),
            error_category="PROVIDER_ERROR"
        )

@mcp.tool()
async def get_issue_details(owner: str, repo: str, issue_number: int) -> Dict[str, Any]:
    """
    Get complete details and comments for a specific issue.
    """
    token = os.getenv("GITHUB_TOKEN", "")
    if not token:
        if is_mock_allowed():
            match = next((i for i in MOCK_ISSUES if i["number"] == issue_number), MOCK_ISSUES[0])
            return create_success_envelope(
                system="github",
                tool="get_issue_details",
                data=match,
                source_mode="mock_sandbox",
                resource_ids_urls=[match["html_url"]]
            )
        return create_error_envelope(
            system="github",
            tool="get_issue_details",
            error="GITHUB_AUTH_REQUIRED: GITHUB_TOKEN is not configured in environment.",
            error_category="UNAUTHENTICATED"
        )

    try:
        async with get_github_client(token) as client:
            resp = await client.get(f"/repos/{owner}/{repo}/issues/{issue_number}")
            if resp.status_code != 200:
                return create_error_envelope(
                    system="github",
                    tool="get_issue_details",
                    error=f"Failed to retrieve issue #{issue_number}: {resp.text}",
                    error_category="NOT_FOUND" if resp.status_code == 404 else "PROVIDER_ERROR"
                )
            data = resp.json()
            cleaned = {
                "number": data.get("number"),
                "title": data.get("title"),
                "state": data.get("state"),
                "author": data.get("user", {}).get("login"),
                "labels": [l.get("name") for l in data.get("labels", [])],
                "body": data.get("body"),
                "html_url": data.get("html_url"),
                "created_at": data.get("created_at"),
                "updated_at": data.get("updated_at")
            }
            return create_success_envelope(
                system="github",
                tool="get_issue_details",
                data=cleaned,
                resource_ids_urls=[cleaned["html_url"]] if cleaned.get("html_url") else []
            )
    except Exception as ex:
        return create_error_envelope(
            system="github",
            tool="get_issue_details",
            error=str(ex),
            error_category="PROVIDER_ERROR"
        )

@mcp.tool()
async def list_pull_requests(
    owner: str,
    repo: str,
    state: str = "open",
    per_page: int = 10
) -> Dict[str, Any]:
    """
    List pull requests from a GitHub repository.
    """
    token = os.getenv("GITHUB_TOKEN", "")
    if not token:
        if is_mock_allowed():
            prs = [
                {
                    "number": 43,
                    "title": "fix: increase max pool size for Postgres connection pool to 80",
                    "state": "open",
                    "user": "lead-dev",
                    "draft": False,
                    "html_url": f"https://github.com/{owner}/{repo}/pull/43",
                    "created_at": "2026-10-13T11:00:00Z"
                }
            ]
            return create_success_envelope(
                system="github",
                tool="list_pull_requests",
                data={"owner": owner, "repo": repo, "count": len(prs), "pull_requests": prs},
                source_mode="mock_sandbox",
                resource_ids_urls=[p["html_url"] for p in prs]
            )
        return create_error_envelope(
            system="github",
            tool="list_pull_requests",
            error="GITHUB_AUTH_REQUIRED: GITHUB_TOKEN is not configured in environment.",
            error_category="UNAUTHENTICATED"
        )

    try:
        async with get_github_client(token) as client:
            resp = await client.get(f"/repos/{owner}/{repo}/pulls", params={"state": state, "per_page": per_page})
            if resp.status_code != 200:
                return create_error_envelope(
                    system="github",
                    tool="list_pull_requests",
                    error=f"Failed to list PRs: {resp.text}",
                    error_category="PROVIDER_ERROR"
                )
            prs = resp.json()
            cleaned = [
                {
                    "number": p.get("number"),
                    "title": p.get("title"),
                    "state": p.get("state"),
                    "user": p.get("user", {}).get("login"),
                    "draft": p.get("draft"),
                    "html_url": p.get("html_url"),
                    "created_at": p.get("created_at")
                }
                for p in prs
            ]
            return create_success_envelope(
                system="github",
                tool="list_pull_requests",
                data={"owner": owner, "repo": repo, "count": len(cleaned), "pull_requests": cleaned},
                resource_ids_urls=[p["html_url"] for p in cleaned if p.get("html_url")]
            )
    except Exception as ex:
        return create_error_envelope(
            system="github",
            tool="list_pull_requests",
            error=str(ex),
            error_category="PROVIDER_ERROR"
        )

@mcp.tool()
async def get_pull_request_details(owner: str, repo: str, pull_number: int) -> Dict[str, Any]:
    """
    Get detailed information about a pull request including merge status, branch names, and diff stats.
    """
    token = os.getenv("GITHUB_TOKEN", "")
    if not token and is_mock_allowed():
        return create_success_envelope(
            system="github",
            tool="get_pull_request_details",
            data={
                "number": pull_number,
                "title": "fix: increase max pool size",
                "state": "open",
                "mergeable": True,
                "merged": False,
                "additions": 14,
                "deletions": 3,
                "changed_files": 2,
                "head_branch": "fix/pool-size",
                "base_branch": "main",
                "html_url": f"https://github.com/{owner}/{repo}/pull/{pull_number}"
            },
            source_mode="mock_sandbox"
        )

    try:
        async with get_github_client(token) as client:
            resp = await client.get(f"/repos/{owner}/{repo}/pulls/{pull_number}")
            if resp.status_code != 200:
                return create_error_envelope(
                    system="github",
                    tool="get_pull_request_details",
                    error=f"Failed to get PR #{pull_number}: {resp.text}",
                    error_category="NOT_FOUND" if resp.status_code == 404 else "PROVIDER_ERROR"
                )
            p = resp.json()
            cleaned = {
                "number": p.get("number"),
                "title": p.get("title"),
                "state": p.get("state"),
                "mergeable": p.get("mergeable"),
                "merged": p.get("merged"),
                "additions": p.get("additions"),
                "deletions": p.get("deletions"),
                "changed_files": p.get("changed_files"),
                "head_branch": p.get("head", {}).get("ref"),
                "base_branch": p.get("base", {}).get("ref"),
                "html_url": p.get("html_url")
            }
            return create_success_envelope(
                system="github",
                tool="get_pull_request_details",
                data=cleaned,
                resource_ids_urls=[cleaned["html_url"]] if cleaned.get("html_url") else []
            )
    except Exception as ex:
        return create_error_envelope(
            system="github",
            tool="get_pull_request_details",
            error=str(ex),
            error_category="PROVIDER_ERROR"
        )

@mcp.tool()
async def list_recent_commits(owner: str, repo: str, per_page: int = 10) -> Dict[str, Any]:
    """
    List recent commits on the default branch.
    """
    token = os.getenv("GITHUB_TOKEN", "")
    if not token and is_mock_allowed():
        commits = [
            {
                "sha": "a7b3c9d",
                "message": "fix: update db timeout settings",
                "author": "Aditya Bhagwat",
                "date": "2026-10-13T09:00:00Z",
                "html_url": f"https://github.com/{owner}/{repo}/commit/a7b3c9d"
            }
        ]
        return create_success_envelope(
            system="github",
            tool="list_recent_commits",
            data={"owner": owner, "repo": repo, "commits": commits},
            source_mode="mock_sandbox"
        )

    try:
        async with get_github_client(token) as client:
            resp = await client.get(f"/repos/{owner}/{repo}/commits", params={"per_page": per_page})
            if resp.status_code != 200:
                return create_error_envelope(
                    system="github",
                    tool="list_recent_commits",
                    error=f"Failed to retrieve commits: {resp.text}",
                    error_category="PROVIDER_ERROR"
                )
            commits = resp.json()
            cleaned = [
                {
                    "sha": c.get("sha")[:8],
                    "message": c.get("commit", {}).get("message"),
                    "author": c.get("commit", {}).get("author", {}).get("name"),
                    "date": c.get("commit", {}).get("author", {}).get("date"),
                    "html_url": c.get("html_url")
                }
                for c in commits
            ]
            return create_success_envelope(
                system="github",
                tool="list_recent_commits",
                data={"owner": owner, "repo": repo, "commits": cleaned},
                resource_ids_urls=[c["html_url"] for c in cleaned if c.get("html_url")]
            )
    except Exception as ex:
        return create_error_envelope(
            system="github",
            tool="list_recent_commits",
            error=str(ex),
            error_category="PROVIDER_ERROR"
        )

@mcp.tool()
async def get_workflow_runs(owner: str, repo: str, per_page: int = 5) -> Dict[str, Any]:
    """
    Retrieve recent GitHub Actions CI/CD workflow runs and their status.
    """
    token = os.getenv("GITHUB_TOKEN", "")
    if not token and is_mock_allowed():
        runs = [
            {
                "id": 89201,
                "name": "Production Deploy",
                "status": "completed",
                "conclusion": "success",
                "event": "push",
                "html_url": f"https://github.com/{owner}/{repo}/actions/runs/89201",
                "created_at": "2026-10-13T08:30:00Z"
            }
        ]
        return create_success_envelope(
            system="github",
            tool="get_workflow_runs",
            data={"owner": owner, "repo": repo, "runs": runs},
            source_mode="mock_sandbox"
        )

    try:
        async with get_github_client(token) as client:
            resp = await client.get(f"/repos/{owner}/{repo}/actions/runs", params={"per_page": per_page})
            if resp.status_code != 200:
                return create_error_envelope(
                    system="github",
                    tool="get_workflow_runs",
                    error=f"Failed to fetch workflow runs: {resp.text}",
                    error_category="PROVIDER_ERROR"
                )
            runs = resp.json().get("workflow_runs", [])
            cleaned = [
                {
                    "id": r.get("id"),
                    "name": r.get("name"),
                    "status": r.get("status"),
                    "conclusion": r.get("conclusion"),
                    "event": r.get("event"),
                    "html_url": r.get("html_url"),
                    "created_at": r.get("created_at")
                }
                for r in runs
            ]
            return create_success_envelope(
                system="github",
                tool="get_workflow_runs",
                data={"owner": owner, "repo": repo, "runs": cleaned},
                resource_ids_urls=[r["html_url"] for r in cleaned if r.get("html_url")]
            )
    except Exception as ex:
        return create_error_envelope(
            system="github",
            tool="get_workflow_runs",
            error=str(ex),
            error_category="PROVIDER_ERROR"
        )

# =========================================================================
# GITHUB WRITE TOOLS (MANDATORY APPROVAL GATE)
# =========================================================================

@mcp.tool()
async def create_issue(
    owner: str,
    repo: str,
    title: str,
    body: str,
    labels: Optional[List[str]] = None,
    approval_token: str = ""
) -> Dict[str, Any]:
    """
    [WRITE OPERATION - REQUIRES APPROVAL]
    Create an actual issue in the specified GitHub repository.
    Strictly verifies that approval_token is signed by the OpsPilot backend approval boundary.
    """
    call_args = {
        "owner": owner,
        "repo": repo,
        "title": title,
        "body": body,
        "labels": labels or []
    }

    if not verify_approval_token("create_issue", call_args, approval_token):
        return create_error_envelope(
            system="github",
            tool="create_issue",
            error="WRITE_APPROVAL_REQUIRED: Creating a live GitHub issue requires explicit human approval.",
            error_category="APPROVAL_REQUIRED",
            is_write=True
        )

    token = os.getenv("GITHUB_TOKEN", "")
    if not token:
        if is_mock_allowed():
            new_num = 44
            url = f"https://github.com/{owner}/{repo}/issues/{new_num}"
            return create_success_envelope(
                system="github",
                tool="create_issue",
                is_write=True,
                data={
                    "status": "SUCCESS",
                    "action": "created_github_issue",
                    "issue_number": new_num,
                    "title": title,
                    "html_url": url,
                    "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat() + "Z",
                    "verified": True
                },
                resource_ids_urls=[url],
                source_mode="mock_sandbox"
            )
        return create_error_envelope(
            system="github",
            tool="create_issue",
            error="GITHUB_TOKEN is missing. Provide a valid token with 'issues:write' or 'repo' scope.",
            error_category="UNAUTHENTICATED",
            is_write=True
        )

    payload = {"title": title, "body": body}
    if labels:
        payload["labels"] = labels

    try:
        async with get_github_client(token) as client:
            resp = await client.post(f"/repos/{owner}/{repo}/issues", json=payload)
            if resp.status_code not in (200, 201):
                return create_error_envelope(
                    system="github",
                    tool="create_issue",
                    error=f"GitHub API rejected issue creation: {resp.text}",
                    error_category="PROVIDER_ERROR",
                    is_write=True
                )
            
            created = resp.json()
            url = created.get("html_url", "")
            return create_success_envelope(
                system="github",
                tool="create_issue",
                is_write=True,
                data={
                    "status": "SUCCESS",
                    "action": "created_github_issue",
                    "issue_number": created.get("number"),
                    "title": created.get("title"),
                    "html_url": url,
                    "created_at": created.get("created_at"),
                    "verified": True
                },
                resource_ids_urls=[url] if url else []
            )
    except Exception as ex:
        return create_error_envelope(
            system="github",
            tool="create_issue",
            error=str(ex),
            error_category="PROVIDER_ERROR",
            is_write=True
        )

@mcp.tool()
async def update_issue(
    owner: str,
    repo: str,
    issue_number: int,
    state: Optional[str] = None,
    title: Optional[str] = None,
    body: Optional[str] = None,
    approval_token: str = ""
) -> Dict[str, Any]:
    """
    [WRITE OPERATION - REQUIRES APPROVAL]
    Update title, body, or state (open/closed) of an existing GitHub issue.
    Requires cryptographic approval_token from the OpsPilot backend approval boundary.
    """
    call_args = {
        "owner": owner,
        "repo": repo,
        "issue_number": issue_number,
        "state": state,
        "title": title,
        "body": body
    }

    if not verify_approval_token("update_issue", call_args, approval_token):
        return create_error_envelope(
            system="github",
            tool="update_issue",
            error="WRITE_APPROVAL_REQUIRED: Modifying an issue requires explicit human approval.",
            error_category="APPROVAL_REQUIRED",
            is_write=True
        )

    token = os.getenv("GITHUB_TOKEN", "")
    if not token and is_mock_allowed():
        url = f"https://github.com/{owner}/{repo}/issues/{issue_number}"
        return create_success_envelope(
            system="github",
            tool="update_issue",
            is_write=True,
            data={
                "status": "SUCCESS",
                "issue_number": issue_number,
                "state": state or "open",
                "html_url": url
            },
            resource_ids_urls=[url],
            source_mode="mock_sandbox"
        )

    payload = {}
    if state: payload["state"] = state
    if title: payload["title"] = title
    if body: payload["body"] = body

    try:
        async with get_github_client(token) as client:
            resp = await client.patch(f"/repos/{owner}/{repo}/issues/{issue_number}", json=payload)
            if resp.status_code != 200:
                return create_error_envelope(
                    system="github",
                    tool="update_issue",
                    error=f"GitHub API error: {resp.text}",
                    error_category="PROVIDER_ERROR",
                    is_write=True
                )
            
            updated = resp.json()
            url = updated.get("html_url", "")
            return create_success_envelope(
                system="github",
                tool="update_issue",
                is_write=True,
                data={
                    "status": "SUCCESS",
                    "issue_number": updated.get("number"),
                    "state": updated.get("state"),
                    "html_url": url
                },
                resource_ids_urls=[url] if url else []
            )
    except Exception as ex:
        return create_error_envelope(
            system="github",
            tool="update_issue",
            error=str(ex),
            error_category="PROVIDER_ERROR",
            is_write=True
        )

@mcp.tool()
async def add_issue_comment(
    owner: str,
    repo: str,
    issue_number: int,
    comment_body: str,
    approval_token: str = ""
) -> Dict[str, Any]:
    """
    [WRITE OPERATION - REQUIRES APPROVAL]
    Post a comment to a GitHub issue.
    Requires cryptographic approval_token from the OpsPilot backend approval boundary.
    """
    call_args = {
        "owner": owner,
        "repo": repo,
        "issue_number": issue_number,
        "comment_body": comment_body
    }

    if not verify_approval_token("add_issue_comment", call_args, approval_token):
        return create_error_envelope(
            system="github",
            tool="add_issue_comment",
            error="WRITE_APPROVAL_REQUIRED: Posting a comment requires explicit human approval.",
            error_category="APPROVAL_REQUIRED",
            is_write=True
        )

    token = os.getenv("GITHUB_TOKEN", "")
    if not token and is_mock_allowed():
        url = f"https://github.com/{owner}/{repo}/issues/{issue_number}#issuecomment-999"
        return create_success_envelope(
            system="github",
            tool="add_issue_comment",
            is_write=True,
            data={
                "status": "SUCCESS",
                "comment_id": 999,
                "html_url": url
            },
            resource_ids_urls=[url],
            source_mode="mock_sandbox"
        )

    try:
        async with get_github_client(token) as client:
            resp = await client.post(
                f"/repos/{owner}/{repo}/issues/{issue_number}/comments",
                json={"body": comment_body}
            )
            if resp.status_code not in (200, 201):
                return create_error_envelope(
                    system="github",
                    tool="add_issue_comment",
                    error=f"GitHub API error: {resp.text}",
                    error_category="PROVIDER_ERROR",
                    is_write=True
                )
            data = resp.json()
            url = data.get("html_url", "")
            return create_success_envelope(
                system="github",
                tool="add_issue_comment",
                is_write=True,
                data={
                    "status": "SUCCESS",
                    "comment_id": data.get("id"),
                    "html_url": url
                },
                resource_ids_urls=[url] if url else []
            )
    except Exception as ex:
        return create_error_envelope(
            system="github",
            tool="add_issue_comment",
            error=str(ex),
            error_category="PROVIDER_ERROR",
            is_write=True
        )

if __name__ == "__main__":
    mcp.run()
