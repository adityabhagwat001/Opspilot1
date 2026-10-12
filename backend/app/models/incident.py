import enum
from datetime import datetime, timezone
from sqlalchemy import Integer, String, Text, DateTime, Enum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class IncidentSeverity(str, enum.Enum):
    """Severity classification of an operational incident."""
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


class IncidentStatus(str, enum.Enum):
    """Lifecycle status of an infrastructure incident."""
    OPEN = "open"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"


class Incident(Base):
    """Operational incident recorded by threshold alerts or manual triage."""
    __tablename__ = "incidents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    node_id: Mapped[str] = mapped_column(String(64), ForeignKey("nodes.id", ondelete="SET NULL"), nullable=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    severity: Mapped[IncidentSeverity] = mapped_column(
        Enum(IncidentSeverity),
        default=IncidentSeverity.WARNING,
        nullable=False
    )
    status: Mapped[IncidentStatus] = mapped_column(
        Enum(IncidentStatus),
        default=IncidentStatus.OPEN,
        nullable=False
    )
    ai_diagnosis: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    resolved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
