#!/bin/sh
# Dev-only API runner: SQLite instead of Postgres so no services are needed.
# Production path is docker-compose (Postgres + Alembic migrations).
cd "$(dirname "$0")/../apps/api"
export DATABASE_URL="sqlite+aiosqlite:///./dev.db"
.venv/bin/python -c "
import asyncio
from app.db import engine
from app.models import Base
async def main():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
asyncio.run(main())
"
exec .venv/bin/uvicorn app.main:app --port 8000
