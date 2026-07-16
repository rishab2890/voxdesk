"""Dograh adapter. Talks to a self-hosted Dograh instance (DOGRAH_URL).
Dograh owns the realtime call loop (Telnyx audio ↔ STT ↔ LLM ↔ TTS) and
posts events to our /webhooks/dograh endpoint. Replaceable by design."""

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
        async with self._client() as c:
            r = await c.put(f"/api/workflows/{agent_id}", json=config)
            r.raise_for_status()
            return r.json().get("id", agent_id)

    async def health(self) -> bool:
        try:
            async with self._client() as c:
                r = await c.get("/health")
                return r.status_code == 200
        except httpx.HTTPError:
            return False
