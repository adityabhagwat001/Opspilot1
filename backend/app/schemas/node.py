from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict

from app.models.node import NodeStatus


class NodeBase(BaseModel):
    """Shared infrastructure node attributes."""
    name: str = Field(..., min_length=2, max_length=128, description="Friendly node moniker")
    hostname: str = Field(..., min_length=2, max_length=255, description="Host system hostname")
    ip_address: Optional[str] = Field(None, description="Host IP address")
    os_info: Optional[str] = Field(None, description="Operating system details")


class NodeRegister(NodeBase):
    """Payload to register a new managed infrastructure node."""
    id: Optional[str] = Field(None, description="Optional custom unique node identifier (e.g. srv-prod-01)")


class NodeResponse(NodeBase):
    """Public node representation."""
    id: str
    status: NodeStatus
    created_at: datetime
    last_heartbeat_at: datetime

    model_config = ConfigDict(from_attributes=True)


class NodeRegisterResponse(BaseModel):
    """Response returned upon successful node registration, containing generated agent secret."""
    node: NodeResponse
    api_key: str = Field(..., description="Secret agent API key (save securely; will not be shown again)")
    message: str = "Node successfully registered. Configure collector with this API key."
