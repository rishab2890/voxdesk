"""Dograh adapter (verified live against Dograh API 1.0.0, self-hosted v1.42).

Integration model: Dograh owns the realtime call — workflow graph, STT/LLM/
TTS, telephony. VoxDesk keeps an agent's workflow linked and ingests finished
workflow *runs* (transcript, recording, status) into calls/transcripts/
summaries (see app.services.dograh_sync).

Auth: an API key from the Dograh UI, sent as the `X-API-Key` header (NOT
Authorization: Bearer). Endpoints live under /api/v1/*."""

import httpx

from app.config import get_settings
from app.providers.base import VoiceEngineProvider


class DograhVoiceEngine(VoiceEngineProvider):
    def __init__(self):
        s = get_settings()
        self.base = s.dograh_url.rstrip("/")
        self.key = s.dograh_api_key

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(base_url=self.base, headers={"X-API-Key": self.key}, timeout=20)

    async def list_workflows(self) -> list[dict]:
        async with self._client() as c:
            r = await c.get("/api/v1/workflow/fetch")
            r.raise_for_status()
            data = r.json()
            return data if isinstance(data, list) else data.get("workflows", data.get("items", []))

    async def sync_agent_workflow(self, agent_id: str, config: dict) -> str:
        """Link a VoxDesk agent to its Dograh workflow by matching names.

        ponytail: workflow *creation* needs Dograh's node-graph schema
        (POST /api/v1/workflow/create/definition); until we generate that from
        an agent's prompt, workflows are built in the Dograh UI. Name match is
        whitespace-insensitive so "Realestate  - inbound" still links."""
        target = " ".join(config.get("name", "").split()).lower()
        try:
            for wf in await self.list_workflows():
                if " ".join(str(wf.get("name", "")).split()).lower() == target:
                    return str(wf.get("id") or wf.get("uuid") or agent_id)
        except httpx.HTTPError:
            pass
        return agent_id

    async def list_runs(self, workflow_id: str | int) -> list[dict]:
        """Call runs for a workflow (summary objects; call get_run for artifacts)."""
        async with self._client() as c:
            r = await c.get(f"/api/v1/workflow/{workflow_id}/runs")
            r.raise_for_status()
            data = r.json()
            return data if isinstance(data, list) else data.get("runs", data.get("items", []))

    async def get_run(self, workflow_id: str | int, run_id: str | int) -> dict:
        """Full run detail — includes populated transcript_public_url /
        recording_public_url (the list endpoint leaves those null)."""
        async with self._client() as c:
            r = await c.get(f"/api/v1/workflow/{workflow_id}/runs/{run_id}")
            r.raise_for_status()
            return r.json()

    async def fetch_transcript(self, public_url: str) -> str:
        """Transcript text via its public download URL (token-auth, no key).
        The URL 302-redirects to object storage, so follow redirects."""
        async with httpx.AsyncClient(timeout=20, follow_redirects=True) as c:
            r = await c.get(public_url)
            r.raise_for_status()
            return r.text

    async def health(self) -> bool:
        try:
            async with self._client() as c:
                r = await c.get("/api/v1/health")
                return r.status_code == 200
        except httpx.HTTPError:
            return False
