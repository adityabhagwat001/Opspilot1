"""
OpsPilot Standardized Typed MCP Response Envelope
Provides structured, truthful telemetry across all custom FastMCP tools.
"""

import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

def utc_iso_now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat() + "Z"

class MCPEnvelope(BaseModel):
    success: bool = True
    system: str  # "postgresql" | "github" | "email" | "calendar"
    tool: str
    is_write: bool = False
    requires_approval: bool = False
    data: Any = None
    resource_ids_urls: List[str] = Field(default_factory=list)
    error: Optional[str] = None
    error_category: Optional[str] = None  # "UNAUTHENTICATED", "NOT_FOUND", "PERMISSION_DENIED", "VALIDATION", "APPROVAL_REQUIRED", "PROVIDER_ERROR"
    source_mode: str = "live_provider"  # "live_provider" | "mock_sandbox"
    timestamp: str = Field(default_factory=utc_iso_now)
    retryable: bool = False

def create_success_envelope(
    system: str,
    tool: str,
    data: Any,
    is_write: bool = False,
    resource_ids_urls: Optional[List[str]] = None,
    source_mode: str = "live_provider"
) -> Dict[str, Any]:
    return MCPEnvelope(
        success=True,
        system=system,
        tool=tool,
        is_write=is_write,
        requires_approval=is_write,
        data=data,
        resource_ids_urls=resource_ids_urls or [],
        source_mode=source_mode,
        retryable=False
    ).model_dump()

def create_error_envelope(
    system: str,
    tool: str,
    error: str,
    error_category: str = "PROVIDER_ERROR",
    is_write: bool = False,
    source_mode: str = "live_provider",
    retryable: bool = False
) -> Dict[str, Any]:
    return MCPEnvelope(
        success=False,
        system=system,
        tool=tool,
        is_write=is_write,
        requires_approval=is_write,
        error=error,
        error_category=error_category,
        source_mode=source_mode,
        retryable=retryable
    ).model_dump()
