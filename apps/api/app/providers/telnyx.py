"""Telnyx adapter. Real HTTP calls, credentials from env — with the
placeholder key it fails loudly, so leave TELEPHONY_PROVIDER=mock until
production configuration."""

import httpx

from app.config import get_settings
from app.providers.base import TelephonyProvider

API = "https://api.telnyx.com/v2"


class TelnyxTelephony(TelephonyProvider):
    def __init__(self):
        self.key = get_settings().telnyx_api_key

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(base_url=API, headers={"Authorization": f"Bearer {self.key}"}, timeout=15)

    async def list_available_numbers(self, area_code: str = "") -> list[str]:
        async with self._client() as c:
            r = await c.get("/available_phone_numbers", params={"filter[national_destination_code]": area_code or "212"})
            r.raise_for_status()
            return [n["phone_number"] for n in r.json().get("data", [])]

    async def provision_number(self, number: str) -> str:
        async with self._client() as c:
            r = await c.post("/number_orders", json={"phone_numbers": [{"phone_number": number}]})
            r.raise_for_status()
            return r.json()["data"]["id"]

    async def transfer_call(self, provider_call_id: str, to_number: str) -> None:
        async with self._client() as c:
            r = await c.post(f"/calls/{provider_call_id}/actions/transfer", json={"to": to_number})
            r.raise_for_status()

    async def hangup(self, provider_call_id: str) -> None:
        async with self._client() as c:
            r = await c.post(f"/calls/{provider_call_id}/actions/hangup", json={})
            r.raise_for_status()
