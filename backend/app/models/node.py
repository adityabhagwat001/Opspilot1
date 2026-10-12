import enum
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, Enum
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class NodeStatus(str, enum.Enum):
    """Operational health state of a registered infrastructure node."""
    ONLINE = "online"
    DEGRADED = "degraded"
    OFFLINE = "offline"


class Node(Base):
    """Registered server or host agent reporting telemetry to OpsPilot."""
    __tablename__ = "nodes"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    hostname: Mapped[str] = mapped_column(String(255), nullable=False)
    ip_address: Mapped[str] = mapped_column(String(64), nullable=True)
    api_key_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    status: Mapped[NodeStatus] = mapped_column(Enum(NodeStatus), default=NodeStatus.ONLINE, nullable=False)
    os_info: Mapped[str] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    last_heartbeat_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
