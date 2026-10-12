from datetime import datetime, timezone
from sqlalchemy import Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class TelemetryMetric(Base):
    """Time-series telemetry metric snapshot ingested from an agent probe."""
    __tablename__ = "telemetry_metrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    node_id: Mapped[str] = mapped_column(String(64), ForeignKey("nodes.id", ondelete="CASCADE"), index=True, nullable=False)
    cpu_usage_pct: Mapped[float] = mapped_column(Float, nullable=False)
    memory_usage_pct: Mapped[float] = mapped_column(Float, nullable=False)
    memory_used_mb: Mapped[float] = mapped_column(Float, nullable=True)
    memory_total_mb: Mapped[float] = mapped_column(Float, nullable=True)
    disk_usage_pct: Mapped[float] = mapped_column(Float, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        index=True,
        nullable=False
    )
