import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_signup_success(client: AsyncClient):
    """
    Tests successful registration of a user account.
    """
    payload = {
        "username": "test_user_auth",
        "password": "securepassword123"
    }
    response = await client.post("/signup", json=payload)
    assert response.status_code == 201
    
    data = response.json()
    assert data["username"] == "test_user_auth"
    assert "id" in data
    assert "created_at" in data

@pytest.mark.asyncio
async def test_signup_duplicate(client: AsyncClient):
    """
    Tests duplicate username checks return HTTP 400.
    """
    payload = {
        "username": "duplicate_user",
        "password": "password123"
    }
    # First signup
    res1 = await client.post("/signup", json=payload)
    assert res1.status_code == 201
    
    # Second signup with same username
    res2 = await client.post("/signup", json=payload)
    assert res2.status_code == 400
    assert "detail" in res2.json()

@pytest.mark.asyncio
async def test_login_success(client: AsyncClient):
    """
    Tests user login returns access tokens.
    """
    # 1. Signup user
    signup_payload = {
        "username": "login_user",
        "password": "loginpassword123"
    }
    await client.post("/signup", json=signup_payload)
    
    # 2. Login
    login_payload = {
        "username": "login_user",
        "password": "loginpassword123"
    }
    response = await client.post("/login", data=login_payload)
    assert response.status_code == 200
    
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

@pytest.mark.asyncio
async def test_login_invalid_credentials(client: AsyncClient):
    """
    Tests invalid login checks return HTTP 401.
    """
    login_payload = {
        "username": "non_existent_user",
        "password": "wrongpassword"
    }
    response = await client.post("/login", data=login_payload)
    assert response.status_code == 401
