"""Env-driven provider factory (dependency inversion point).
Add a provider: write the adapter, register it here, set the env var."""

from functools import lru_cache

from app.config import get_settings
from app.providers import mock
from app.providers.base import (
    CalendarProvider,
    CRMProvider,
    EmbeddingProvider,
    LLMProvider,
    StorageProvider,
    STTProvider,
    TelephonyProvider,
    TTSProvider,
    VoiceEngineProvider,
)


def _pick(kind: str, name: str, table: dict):
    try:
        return table[name]()
    except KeyError:
        raise ValueError(f"Unknown {kind} provider: {name!r}. Options: {sorted(table)}")


@lru_cache
def get_llm() -> LLMProvider:
    return _pick("llm", get_settings().llm_provider, {"mock": mock.MockLLM})


@lru_cache
def get_stt() -> STTProvider:
    return _pick("stt", get_settings().stt_provider, {"mock": mock.MockSTT})


@lru_cache
def get_tts() -> TTSProvider:
    return _pick("tts", get_settings().tts_provider, {"mock": mock.MockTTS})


@lru_cache
def get_embeddings() -> EmbeddingProvider:
    return _pick("embedding", get_settings().embedding_provider, {"mock": mock.MockEmbeddings})


@lru_cache
def get_telephony() -> TelephonyProvider:
    from app.providers.telnyx import TelnyxTelephony

    return _pick("telephony", get_settings().telephony_provider,
                 {"mock": mock.MockTelephony, "telnyx": TelnyxTelephony})


@lru_cache
def get_voice_engine() -> VoiceEngineProvider:
    from app.providers.dograh import DograhVoiceEngine

    return _pick("voice engine", get_settings().voice_engine,
                 {"mock": mock.MockVoiceEngine, "dograh": DograhVoiceEngine})


@lru_cache
def get_calendar() -> CalendarProvider:
    return _pick("calendar", get_settings().calendar_provider, {"mock": mock.MockCalendar})


@lru_cache
def get_crm() -> CRMProvider:
    return _pick("crm", get_settings().crm_provider, {"mock": mock.MockCRM})


@lru_cache
def get_storage() -> StorageProvider:
    s = get_settings()
    return _pick("storage", s.storage_provider, {"local": lambda: mock.LocalStorage(s.storage_dir)})
