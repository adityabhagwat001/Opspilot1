"""
OpsPilot Enterprise Centralized Role-Based Access Control (RBAC) Permission Matrix
Defines system roles, granular permission strings, and role-to-permission mappings.
"""

from typing import Dict, Set, List

# Role Identifiers
ROLE_ADMIN = "admin"
ROLE_OPERATOR = "operator"
ROLE_VIEWER = "viewer"

# Granular Permission Identifiers
DASHBOARD_READ = "dashboard:read"
AI_CHAT = "ai:chat"
AI_ANALYZE = "ai:analyze"

GITHUB_READ = "github:read"
GITHUB_PROPOSE_FIX = "github:propose_fix"
GITHUB_EXECUTE_APPROVED_FIX = "github:execute_approved_fix"
GITHUB_MANAGE_INTEGRATIONS = "github:manage_integrations"

DATABASE_READ = "database:read"
DATABASE_PROPOSE_WRITE = "database:propose_write"
DATABASE_EXECUTE_APPROVED_WRITE = "database:execute_approved_write"

APPROVAL_CREATE = "approval:create"
APPROVAL_READ = "approval:read"
APPROVAL_APPROVE = "approval:approve"
APPROVAL_REJECT = "approval:reject"

AUDIT_READ_OWN = "audit:read_own"
AUDIT_READ_ALL = "audit:read_all"

INTEGRATION_READ = "integration:read"
INTEGRATION_MANAGE = "integration:manage"

USERS_MANAGE = "users:manage"
SETTINGS_MANAGE = "settings:manage"
SYSTEM_HEALTH_READ = "system:health_read"

# Centralized Role -> Permissions Mapping
ROLE_PERMISSIONS: Dict[str, Set[str]] = {
    ROLE_OPERATOR: {
        DASHBOARD_READ,
        AI_CHAT,
        AI_ANALYZE,
        GITHUB_READ,
        GITHUB_PROPOSE_FIX,
        DATABASE_READ,
        DATABASE_PROPOSE_WRITE,
        APPROVAL_CREATE,
        APPROVAL_READ,
        AUDIT_READ_OWN,
        INTEGRATION_READ,
        SYSTEM_HEALTH_READ,
    },
    ROLE_ADMIN: {
        DASHBOARD_READ,
        AI_CHAT,
        AI_ANALYZE,
        GITHUB_READ,
        GITHUB_PROPOSE_FIX,
        GITHUB_EXECUTE_APPROVED_FIX,
        GITHUB_MANAGE_INTEGRATIONS,
        DATABASE_READ,
        DATABASE_PROPOSE_WRITE,
        DATABASE_EXECUTE_APPROVED_WRITE,
        APPROVAL_CREATE,
        APPROVAL_READ,
        APPROVAL_APPROVE,
        APPROVAL_REJECT,
        AUDIT_READ_OWN,
        AUDIT_READ_ALL,
        INTEGRATION_READ,
        INTEGRATION_MANAGE,
        USERS_MANAGE,
        SETTINGS_MANAGE,
        SYSTEM_HEALTH_READ,
    },
    ROLE_VIEWER: {
        DASHBOARD_READ,
        GITHUB_READ,
        DATABASE_READ,
        APPROVAL_READ,
        AUDIT_READ_OWN,
        INTEGRATION_READ,
        SYSTEM_HEALTH_READ,
    }
}

def has_permission(role: str, permission: str) -> bool:
    """Checks whether a given role holds the requested permission."""
    permissions = ROLE_PERMISSIONS.get(role, set())
    return permission in permissions

def get_role_permissions(role: str) -> List[str]:
    """Returns the sorted list of granted permissions for a given role."""
    return sorted(list(ROLE_PERMISSIONS.get(role, set())))
