"""Fully functional placeholder providers. Deterministic, no network, no
credentials — the whole platform runs end-to-end on these until real
providers are configured via env vars."""

import hashlib
import io
import math
import os
import struct
import uuid
import wave
from datetime import datetime, timedelta, timezone

from app.providers.base import (
    CalendarProvider,
    ChatMessage,
    ChatResult,
    CRMProvider,
    EmbeddingProvider,
    LLMProvider,
    StorageProvider,
    STTProvider,
    TelephonyProvider,
    TimeSlot,
    TTSProvider,
    VoiceEngineProvider,
)

BOOK_TOOL = "book_appointment"
TRANSFER_TOOL = "transfer_to_human"


class MockLLM(LLMProvider):
    """Keyword-routed receptionist. Emits the same tool-call shapes a real
    LLM would, so the voice pipeline exercises identical code paths."""

    async def chat(self, messages: list[ChatMessage], tools: list[dict] | None = None) -> ChatResult:
        last_user = next((m.content for m in reversed(messages) if m.role == "user"), "")
        context = next((m.content for m in messages if m.role == "system" and "Context:" in m.content), "")
        low = last_user.lower()

        if messages and messages[-1].role == "system" and "Summarize" in messages[-1].content:
            turns = [m for m in messages if m.role in ("user", "assistant")]
            return ChatResult(content=f"Call with {len(turns)} exchanges. Topics: {last_user[:120] or 'general inquiry'}.")

        if any(w in low for w in ("human", "person", "transfer", "representative", "manager")):
            return ChatResult(content="Of course, let me transfer you to a team member.",
                              tool_calls=[{"name": TRANSFER_TOOL, "arguments": {}}])
        if any(w in low for w in ("appointment", "book", "schedule", "reservation")):
            starts = (datetime.now(timezone.utc) + timedelta(days=1)).replace(minute=0, second=0, microsecond=0)
            return ChatResult(content="I can book that for you. I've scheduled a slot tomorrow.",
                              tool_calls=[{"name": BOOK_TOOL, "arguments": {"starts_at": starts.isoformat(), "duration_min": 30}}])
        if context:
            snippet = context.split("Context:", 1)[1].strip()[:200]
            return ChatResult(content=f"Based on our records: {snippet}")
        return ChatResult(content="Thanks for calling! Could you tell me a bit more about what you need?")


class MockSTT(STTProvider):
    async def transcribe(self, audio: bytes, language: str = "en-US") -> str:
        # In simulation the "audio" is UTF-8 text; a real adapter decodes speech.
        return audio.decode("utf-8", errors="ignore")


SAMPLE_RATE = 16000


def tone_wav(text: str, freq: float) -> bytes:
    """Real, playable 16-bit mono WAV: a soft tone whose length tracks the
    text, so mock call recordings actually play in the dashboard."""
    duration = min(0.3 + 0.025 * len(text), 2.5)
    n = int(SAMPLE_RATE * duration)
    frames = bytearray()
    for i in range(n):
        envelope = min(1.0, i / 400, (n - i) / 400)  # fade in/out, no clicks
        sample = int(8000 * envelope * math.sin(2 * math.pi * freq * i / SAMPLE_RATE))
        frames += struct.pack("<h", sample)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SAMPLE_RATE)
        w.writeframes(bytes(frames))
    return buf.getvalue()


def concat_wavs(parts: list[bytes]) -> bytes:
    """Concatenate same-format WAV segments into one file."""
    buf = io.BytesIO()
    out: wave.Wave_write | None = None
    for part in parts:
        with wave.open(io.BytesIO(part), "rb") as r:
            if out is None:
                out = wave.open(buf, "wb")
                out.setparams(r.getparams())
            out.writeframes(r.readframes(r.getnframes()))
    if out is None:
        return b""
    out.close()
    return buf.getvalue()


class MockTTS(TTSProvider):
    async def synthesize(self, text: str, voice: str = "default") -> bytes:
        # Pitch derived from the voice name so different speakers sound distinct.
        freq = 300 + (int(hashlib.md5(voice.encode()).hexdigest(), 16) % 200)
        return tone_wav(text, freq)


class MockEmbeddings(EmbeddingProvider):
    """Deterministic pseudo-embeddings: token hashes folded into a unit
    vector. Enough signal for keyword-overlap retrieval in demos."""

    dimensions = 384

    async def embed(self, texts: list[str]) -> list[list[float]]:
        out = []
        for text in texts:
            vec = [0.0] * self.dimensions
            for token in text.lower().split():
                h = int(hashlib.md5(token.encode()).hexdigest(), 16)
                vec[h % self.dimensions] += 1.0
            norm = math.sqrt(sum(v * v for v in vec)) or 1.0
            out.append([v / norm for v in vec])
        return out


class MockTelephony(TelephonyProvider):
    async def list_available_numbers(self, area_code: str = "") -> list[str]:
        prefix = area_code or "555"
        return [f"+1{prefix}01{i:05d}" for i in range(1, 4)]

    async def provision_number(self, number: str) -> str:
        return f"mock-num-{number}"

    async def transfer_call(self, provider_call_id: str, to_number: str) -> None:
        return None

    async def hangup(self, provider_call_id: str) -> None:
        return None


class MockVoiceEngine(VoiceEngineProvider):
    async def sync_agent_workflow(self, agent_id: str, config: dict) -> str:
        return f"mock-workflow-{agent_id}"

    async def health(self) -> bool:
        return True


class MockCalendar(CalendarProvider):
    async def list_slots(self, day: datetime, duration_min: int = 30) -> list[TimeSlot]:
        base = day.replace(hour=9, minute=0, second=0, microsecond=0)
        return [TimeSlot(base + timedelta(minutes=duration_min * i), base + timedelta(minutes=duration_min * (i + 1)))
                for i in range(6)]

    async def book(self, slot: TimeSlot, contact_name: str, contact_phone: str) -> str:
        return f"mock-event-{uuid.uuid4()}"


class MockCRM(CRMProvider):
    async def upsert_contact(self, name: str, phone: str, meta: dict | None = None) -> str:
        return f"mock-contact-{hashlib.md5(phone.encode()).hexdigest()[:12]}"


class LocalStorage(StorageProvider):
    """Filesystem-backed object storage; MinIO/S3 adapter swaps in via env."""

    def __init__(self, root: str):
        self.root = root
        os.makedirs(root, exist_ok=True)

    def _path(self, key: str) -> str:
        safe = key.replace("..", "_").lstrip("/")
        return os.path.join(self.root, safe)

    async def put(self, key: str, data: bytes) -> None:
        path = self._path(key)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            f.write(data)

    async def get(self, key: str) -> bytes:
        with open(self._path(key), "rb") as f:
            return f.read()
