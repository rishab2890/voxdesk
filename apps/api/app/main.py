import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers import agents, analytics, appointments, auth, calls, documents, integrations, organizations, webhooks

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="VoxDesk API", version="0.1.0",
                  description="Multi-tenant AI voice receptionist platform")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[o.strip() for o in settings.cors_origins.split(",")],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    for router in (auth.router, organizations.router, agents.router, agents.numbers,
                   documents.router, calls.router, appointments.router,
                   integrations.router, analytics.router, webhooks.router):
        app.include_router(router)

    @app.get("/health", tags=["health"])
    async def health():
        return {"status": "ok", "service": "voxdesk-api"}

    return app


app = create_app()
