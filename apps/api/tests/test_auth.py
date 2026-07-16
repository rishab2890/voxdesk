import pytest

pytestmark = pytest.mark.asyncio


async def test_register_login_me(client):
    r = await client.post("/auth/register", json={
        "email": "a@b.com", "password": "password123", "name": "A", "organization_name": "Org"})
    assert r.status_code == 201
    token = r.json()["access_token"]

    r = await client.post("/auth/login", json={"email": "a@b.com", "password": "password123"})
    assert r.status_code == 200

    r = await client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["email"] == "a@b.com"


async def test_bad_login_and_missing_token(client):
    r = await client.post("/auth/login", json={"email": "no@one.com", "password": "wrongpass1"})
    assert r.status_code == 401
    r = await client.get("/agents")
    assert r.status_code == 401
