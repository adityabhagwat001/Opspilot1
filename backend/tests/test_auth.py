import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_first_user_becomes_admin(client: AsyncClient):
    """The very first user registered in the system should automatically be granted the admin role."""
    payload = {
        "email": "admin@opspilot.com",
        "password": "Password123!",
        "full_name": "OpsPilot Root Administrator"
    }
    response = await client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "admin@opspilot.com"
    assert data["role"] == "admin"
    assert data["is_active"] is True
    assert "id" in data


@pytest.mark.asyncio
async def test_register_duplicate_email_fails(client: AsyncClient):
    """Registering with an already existing email address should return HTTP 409 Conflict."""
    payload = {
        "email": "admin@opspilot.com",
        "password": "AnotherPassword123!",
        "full_name": "Imposter"
    }
    response = await client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 409
    assert "already exists" in response.json()["detail"]


@pytest.mark.asyncio
async def test_register_second_user_defaults_to_operator(client: AsyncClient):
    """Subsequent registrations should default to operator role."""
    payload = {
        "email": "devops@opspilot.com",
        "password": "SecurePassword999!",
        "full_name": "DevOps Engineer"
    }
    response = await client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "devops@opspilot.com"
    assert data["role"] == "operator"


@pytest.mark.asyncio
async def test_login_invalid_credentials(client: AsyncClient):
    """Login with invalid password returns 401 Unauthorized."""
    payload = {
        "email": "admin@opspilot.com",
        "password": "WrongPassword!"
    }
    response = await client.post("/api/v1/auth/login", json=payload)
    assert response.status_code == 401
    assert "Incorrect email" in response.json()["detail"]


@pytest.mark.asyncio
async def test_login_success_returns_jwt_token(client: AsyncClient):
    """Login with valid credentials returns Bearer access token and user profile."""
    payload = {
        "email": "admin@opspilot.com",
        "password": "Password123!"
    }
    response = await client.post("/api/v1/auth/login", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "admin@opspilot.com"
    assert data["user"]["role"] == "admin"


@pytest.mark.asyncio
async def test_get_me_profile_with_jwt_token(client: AsyncClient):
    """Fetching /me endpoint with valid Bearer token returns current user profile."""
    login_resp = await client.post("/api/v1/auth/login", json={
        "email": "admin@opspilot.com",
        "password": "Password123!"
    })
    token = login_resp.json()["access_token"]

    me_resp = await client.get("/api/v1/auth/me", headers={
        "Authorization": f"Bearer {token}"
    })
    assert me_resp.status_code == 200
    me_data = me_resp.json()
    assert me_data["email"] == "admin@opspilot.com"
    assert me_data["role"] == "admin"


@pytest.mark.asyncio
async def test_get_me_unauthorized_without_token(client: AsyncClient):
    """Requesting /me without Authorization header returns 401 Unauthorized."""
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401
