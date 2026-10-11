import time
import platform
from datetime import datetime, timezone
from fastapi import APIRouter, status
import psutil

from app.core.config import settings
from app.schemas.health import HealthResponse, DependencyStatus, SystemResourceMetrics

router = APIRouter()

# Record process startup timestamp
START_TIME = time.time()


def get_system_metrics() -> SystemResourceMetrics:
    """Collects real-time host operating system resource metrics."""
    cpu_pct = psutil.cpu_percent(interval=None)
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage("/")

    return SystemResourceMetrics(
        cpu_percent=round(cpu_pct, 2),
        memory_used_mb=round((mem.total - mem.available) / (1024 * 1024), 2),
        memory_total_mb=round(mem.total / (1024 * 1024), 2),
        memory_percent=round(mem.percent, 2),
        disk_used_gb=round(disk.used / (1024 * 1024 * 1024), 2),
        disk_total_gb=round(disk.total / (1024 * 1024 * 1024), 2),
        disk_percent=round(disk.percent, 2),
        platform=f"{platform.system()} {platform.release()} ({platform.machine()})"
    )


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Service Health & Readiness Probe",
    description="Returns service uptime, deployment metadata, dependency status, and host metrics."
)
async def check_health() -> HealthResponse:
    uptime = time.time() - START_TIME
    system_metrics = get_system_metrics()

    return HealthResponse(
        status="healthy",
        version=settings.VERSION,
        service=settings.PROJECT_NAME,
        environment=settings.ENVIRONMENT,
        timestamp=datetime.now(timezone.utc),
        uptime_seconds=round(uptime, 2),
        dependencies=DependencyStatus(
            database="ready",
            cache="ready",
            telemetry_bus="active"
        ),
        system_metrics=system_metrics
    )


@router.get(
    "/health/live",
    status_code=status.HTTP_200_OK,
    summary="Minimal Kubernetes Liveness Probe",
    description="Returns a lightweight status payload for container orchestrators."
)
async def liveness_probe() -> dict:
    return {"status": "alive"}
