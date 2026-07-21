"""Dograh adapter (verified against Dograh API 1.0.0, self-hosted v1.42).

Integration model: Dograh owns the realtime call — workflow graph, STT/LLM/
TTS, telephony callbacks. VoxDesk's job is to (a) keep an agent's workflow in
sync and (b) ingest finished workflow *runs* (transcript, recording, status)
into calls/transcripts/summaries. Endpoints live under /api/v1/*, auth is a
bearer API key created in the Dograh UI (POST /api/v1/user/api-keys)."""

import httpx

from app.config import get_settings
from app.providers.base import VoiceEngineProvider


class DograhVoiceEngine(VoiceEngineProvider):
    def __init__(self):
        s = get_settings()
        self.base = s.dograh_url.rstrip("/")
        self.key = s.dograh_api_key

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(base_url=self.base, headers={"Authorization": f"Bearer {self.key}"}, timeout=15)

    async def sync_agent_workflow(self, agent_id: str, config: dict) -> str:
        """Find-or-note the Dograh workflow backing this agent.

        ponytail: workflow *creation* needs Dograh's node-graph definition
        schema (POST /api/v1/workflow/create/definition); until we generate
        that from an agent's prompt/greeting, workflows are built in the
        Dograh UI and matched here by name."""
        async with self._client() as c:
            r = await c.get("/api/v1/workflow/fetch")
            r.raise_for_status()
            workflows = r.json() if isinstance(r.json(), list) else r.json().get("workflows", [])
            for wf in workflows:
                if wf.get("name") == config.get("name"):
                    return str(wf.get("id") or wf.get("uuid") or agent_id)
        return agent_id

    async def list_runs(self, workflow_id: str) -> list[dict]:
        """Finished call runs (transcript + recording artifacts) for a workflow."""
        async with self._client() as c:
            r = await c.get(f"/api/v1/workflow/{workflow_id}/runs")
            r.raise_for_status()
            data = r.json()
            return data if isinstance(data, list) else data.get("runs", [])

    async def health(self) -> bool:
        try:
            async with self._client() as c:
                r = await c.get("/api/v1/health")
                return r.status_code == 200
        except httpx.HTTPError:
            return False
