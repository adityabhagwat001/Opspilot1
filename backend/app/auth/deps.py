"""
Authentication & RBAC Dependencies
Enforces strict JWT token validation, eliminates anonymous fallback,
and guarantees workspace authorization checks.
"""

from typing import Optional
from fastapi import Depends, HTTPException, Header, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.db import get_db
from app.core.security import decode_access_token
from app.models.models import User, Workspace, WorkspaceMember

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)

async def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Strictly verifies JWT Bearer token.
    Zero unauthenticated administrator fallback in ANY environment.
    """
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token required. Anonymous access is strictly prohibited."
        )

    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token"
        )

    stmt = select(User).where(User.id == payload["sub"])
    user = (await db.execute(stmt)).scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )

    return user

async def get_current_workspace_member(
    x_workspace_id: Optional[str] = Header(None, alias="X-Workspace-Id"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> WorkspaceMember:
    """
    Validates workspace membership for the authenticated user.
    Prevents cross-tenant and cross-workspace access.
    """
    target_workspace_id = x_workspace_id or "default-ops"
    
    # Check workspace existence
    ws_stmt = select(Workspace).where(Workspace.id == target_workspace_id)
    ws = (await db.execute(ws_stmt)).scalar_one_or_none()
    if not ws:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workspace '{target_workspace_id}' not found."
        )

    # Check membership
    mem_stmt = select(WorkspaceMember).where(
        WorkspaceMember.workspace_id == target_workspace_id,
        WorkspaceMember.user_id == user.id
    )
    membership = (await db.execute(mem_stmt)).scalar_one_or_none()
    
    if not membership:
        if user.role == "admin":
            # Platform administrators have supervisory access
            return WorkspaceMember(
                id=f"admin-member-{user.id}",
                workspace_id=target_workspace_id,
                user_id=user.id,
                role="admin"
            )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied: You are not a member of workspace '{target_workspace_id}'."
        )

    return membership

def require_role(allowed_roles: list[str]):
    async def role_checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Action requires one of the following roles: {allowed_roles}"
            )
        return user
    return role_checker
