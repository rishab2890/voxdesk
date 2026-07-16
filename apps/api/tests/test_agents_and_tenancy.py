import pytest

pytestmark = pytest.mark.asyncio


async def test_agent_crud(client, auth_headers):
    r = await client.post("/agents", json={"name": "Front Desk"}, headers=auth_headers)
    assert r.status_code == 201
    agent_id = r.json()["id"]

    r = await client.get("/agents", headers=auth_headers)
    assert [a["id"] for a in r.json()] == [agent_id]

    r = await client.put(f"/agents/{agent_id}", json={"name": "Renamed"}, headers=auth_headers)
    assert r.json()["name"] == "Renamed"

    r = await client.delete(f"/agents/{agent_id}", headers=auth_headers)
    assert r.status_code == 204
    r = await client.get("/agents", headers=auth_headers)
    assert r.json() == []


async def test_tenant_isolation(client, auth_headers):
    r = await client.post("/agents", json={"name": "Org1 Agent"}, headers=auth_headers)
    agent_id = r.json()["id"]

    r = await client.post("/auth/register", json={
        "email": "other@example.com", "password": "password123",
        "name": "Other", "organization_name": "OtherOrg"})
    other = {"Authorization": f"Bearer {r.json()['access_token']}"}

    r = await client.get("/agents", headers=other)
    assert r.json() == []
    r = await client.get(f"/agents/{agent_id}", headers=other)
    assert r.status_code == 404
