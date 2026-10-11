from datetime import datetime
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field


class DependencyStatus(BaseModel):
    """Health check status for individual system dependencies."""
    database: str = Field(default="configured", description="Database connectivity status")
    cache: str = Field(default="configured", description="Cache / Redis connectivity status")
    telemetry_bus: str = Field(default="active", description="Telemetry bus status")


class SystemResourceMetrics(BaseModel):
    """Host machine resource consumption metrics."""
    cpu_percent: float = Field(..., description="Current CPU utilization percentage")
    memory_used_mb: float = Field(..., description="Current memory used in MB")
    memory_total_mb: float = Field(..., description="Total system memory in MB")
    memory_percent: float = Field(..., description="Memory utilization percentage")
    disk_used_gb: float = Field(..., description="Disk used in GB")
    disk_total_gb: float = Field(..., description="Disk total in GB")
    disk_percent: float = Field(..., description="Disk utilization percentage")
    platform: str = Field(..., description="Operating system platform details")


class HealthResponse(BaseModel):
    """Standard health response payload for liveness and readiness probes."""
    status: str = Field(default="healthy", description="Overall service status")
    version: str = Field(..., description="Service version string")
    service: str = Field(..., description="Service identifier")
    environment: str = Field(..., description="Deployment environment")
    timestamp: datetime = Field(..., description="Current ISO UTC timestamp")
    uptime_seconds: float = Field(..., description="Process uptime in seconds")
    dependencies: DependencyStatus = Field(default_factory=DependencyStatus)
    system_metrics: Optional[SystemResourceMetrics] = None
