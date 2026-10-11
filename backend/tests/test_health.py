import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_root_endpoint(client: AsyncClient):
    """Verify that root endpoint returns service metadata."""
    response = await client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "service" in data
    assert "version" in data
    assert data["service"] == "OpsPilot Core"


@pytest.mark.asyncio
async def test_health_endpoint(client: AsyncClient):
    """Verify that health check probe returns expected schema and telemetry."""
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["version"] == "0.1.0"
    assert "uptime_seconds" in data
    assert "timestamp" in data
    assert "dependencies" in data
    assert data["dependencies"]["database"] == "ready"
    assert data["dependencies"]["telemetry_bus"] == "active"
    assert "system_metrics" in data
    assert data["system_metrics"]["cpu_percent"] >= 0.0
    assert data["system_metrics"]["memory_total_mb"] > 0


@pytest.mark.asyncio
async def test_liveness_probe(client: AsyncClient):
    """Verify that Kubernetes liveness endpoint responds quickly."""
    response = await client.get("/api/v1/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "alive"}
