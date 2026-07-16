"""Provider interfaces. Business logic depends only on these ABCs;
concrete adapters (mock, telnyx, dograh, qwen, …) are chosen by env config
in app.providers.registry. Swapping a provider = new adapter + env var."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class ChatMessage:
    role: str  # system | user | assistant | tool
    content: str


@dataclass
class ChatResult:
    content: str
    tool_calls: list[dict] = field(default_factory=list)  # [{"name": ..., "arguments": {...}}]


class LLMProvider(ABC):
    @abstractmethod
    async def chat(self, messages: list[ChatMessage], tools: list[dict] | None = None) -> ChatResult: ...


class STTProvider(ABC):
    @abstractmethod
    async def transcribe(self, audio: bytes, language: str = "en-US") -> str: ...


class TTSProvider(ABC):
    @abstractmethod
    async def synthesize(self, text: str, voice: str = "default") -> bytes: ...


class EmbeddingProvider(ABC):
    dimensions: int = 384

    @abstractmethod
    async def embed(self, texts: list[str]) -> list[list[float]]: ...


class TelephonyProvider(ABC):
    @abstractmethod
    async def list_available_numbers(self, area_code: str = "") -> list[str]: ...

    @abstractmethod
    async def provision_number(self, number: str) -> str:
        """Returns the provider's id for the number."""

    @abstractmethod
    async def transfer_call(self, provider_call_id: str, to_number: str) -> None: ...

    @abstractmethod
    async def hangup(self, provider_call_id: str) -> None: ...


class VoiceEngineProvider(ABC):
    """The voice orchestrator (Dograh). Owns the realtime audio loop;
    our backend configures workflows and receives its webhooks."""

    @abstractmethod
    async def sync_agent_workflow(self, agent_id: str, config: dict) -> str:
        """Create/update the engine-side workflow, return its external id."""

    @abstractmethod
    async def health(self) -> bool: ...


@dataclass
class TimeSlot:
    starts_at: datetime
    ends_at: datetime


class CalendarProvider(ABC):
    @abstractmethod
    async def list_slots(self, day: datetime, duration_min: int = 30) -> list[TimeSlot]: ...

    @abstractmethod
    async def book(self, slot: TimeSlot, contact_name: str, contact_phone: str) -> str:
        """Returns external event id."""


class CRMProvider(ABC):
    @abstractmethod
    async def upsert_contact(self, name: str, phone: str, meta: dict | None = None) -> str:
        """Returns external contact id."""


class StorageProvider(ABC):
    @abstractmethod
    async def put(self, key: str, data: bytes) -> None: ...

    @abstractmethod
    async def get(self, key: str) -> bytes: ...
