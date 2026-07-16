"""Tests run against in-memory SQLite (aiosqlite) so no services are needed.
Qdrant/Redis are absent → the code exercises its documented fallbacks."""

import os

os.environ["DATABASE_URL"] = "sqlite+aiosqlite://"
os.environ["REDIS_URL"] = "redis://localhost:1/0"  # unreachable on purpose
os.environ["QDRANT_URL"] = "http://localhost:1"

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.db import engine
from app.main import app
from app.models import Base


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest_asyncio.fixture
async def client():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def auth_headers(client):
    r = await client.post("/auth/register", json={
        "email": "owner@example.com", "password": "password123",
        "name": "Owner", "organization_name": "Acme", "industry": "general",
    })
    assert r.status_code == 201, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}
