import pytest
from httpx import AsyncClient


@pytest.fixture
async def admin_token(client: AsyncClient) -> str:
    """Fixture providing an admin JWT access token."""
    await client.post("/api/v1/auth/register", json={
        "email": "root@opspilot.com",
        "password": "PasswordAdmin123!",
        "full_name": "Root Admin",
        "role": "admin"
    })
    login_resp = await client.post("/api/v1/auth/login", json={
        "email": "root@opspilot.com",
        "password": "PasswordAdmin123!"
    })
    return login_resp.json()["access_token"]


@pytest.fixture
async def viewer_token(client: AsyncClient) -> str:
    """Fixture providing a viewer JWT access token."""
    await client.post("/api/v1/auth/register", json={
        "email": "viewer@opspilot.com",
        "password": "PasswordViewer123!",
        "full_name": "Read Only Viewer",
        "role": "viewer"
    })
    login_resp = await client.post("/api/v1/auth/login", json={
        "email": "viewer@opspilot.com",
        "password": "PasswordViewer123!"
    })
    return login_resp.json()["access_token"]


@pytest.mark.asyncio
async def test_register_node_as_admin(client: AsyncClient, admin_token: str):
    """Admin or operator can successfully register an infrastructure node and receives API key."""
    payload = {
        "id": "srv-prod-worker-01",
        "name": "Production Worker Node 1",
        "hostname": "k8s-worker-1.internal",
        "ip_address": "10.0.1.101",
        "os_info": "Ubuntu 24.04 LTS"
    }
    response = await client.post(
        "/api/v1/nodes/register",
        json=payload,
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["node"]["id"] == "srv-prod-worker-01"
    assert data["node"]["status"] == "online"
    assert "api_key" in data
    assert data["api_key"].startswith("op_")


@pytest.mark.asyncio
async def test_register_node_forbidden_for_viewer(client: AsyncClient, viewer_token: str):
    """Viewer role must be rejected with 403 Forbidden when attempting to register a node."""
    payload = {
        "name": "Unauthorized Node",
        "hostname": "rogue-host"
    }
    response = await client.post(
        "/api/v1/nodes/register",
        json=payload,
        headers={"Authorization": f"Bearer {viewer_token}"}
    )
    assert response.status_code == 403
    assert "requires one of the following roles" in response.json()["detail"]


@pytest.mark.asyncio
async def test_list_nodes(client: AsyncClient, admin_token: str):
    """Authenticated user can list managed infrastructure nodes."""
    response = await client.get(
        "/api/v1/nodes",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    assert any(n["id"] == "srv-prod-worker-01" for n in data)


@pytest.mark.asyncio
async def test_delete_node_as_admin(client: AsyncClient, admin_token: str):
    """Admin can decommission a registered node."""
    response = await client.delete(
        "/api/v1/nodes/srv-prod-worker-01",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "success"

    # Verify node no longer exists
    get_resp = await client.get(
        "/api/v1/nodes/srv-prod-worker-01",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert get_resp.status_code == 404
