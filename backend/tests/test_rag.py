import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_upload_unauthorized(client: AsyncClient):
    """
    Tests upload endpoint returns 401 Unauthorized if no token is provided.
    """
    # Create empty dummy file contents
    files = {"file": ("test.pdf", b"dummy content", "application/pdf")}
    response = await client.post("/upload", files=files)
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_query_unauthorized(client: AsyncClient):
    """
    Tests query endpoint returns 401 Unauthorized if no token is provided.
    """
    payload = {
        "question": "What is RAG?",
        "session_id": "test_session_id"
    }
    response = await client.post("/query", json=payload)
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_sessions_unauthorized(client: AsyncClient):
    """
    Tests sessions listing endpoint returns 401 if unauthorized.
    """
    response = await client.get("/sessions")
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_admin_stats_flow(client: AsyncClient):
    """
    Tests registering, logging in, and retrieving admin statistics.
    """
    # 1. Signup and login to get token
    signup_payload = {
        "username": "admin_test",
        "password": "adminpassword123"
    }
    await client.post("/signup", json=signup_payload)
    
    login_payload = {
        "username": "admin_test",
        "password": "adminpassword123"
    }
    login_res = await client.post("/login", data=login_payload)
    token = login_res.json()["access_token"]
    
    # 2. Get stats with Bearer Token
    headers = {"Authorization": f"Bearer {token}"}
    response = await client.get("/admin/stats", headers=headers)
    assert response.status_code == 200
    
    stats = response.json()
    assert "total_users" in stats
    assert "total_chats" in stats
    assert "uploaded_documents" in stats
    assert "number_of_chunks" in stats
    assert "query_count" in stats
    assert "cache_hits" in stats
    assert "average_response_time" in stats
    
    # Verify we have at least 1 user in stats (our admin_test user)
    assert stats["total_users"] >= 1
