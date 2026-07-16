"""All persistent entities. Multi-tenant: every org-owned row carries
organization_id and queries must filter on it (enforced in app.deps)."""

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)  # soft delete


class Role(str, enum.Enum):
    owner = "owner"
    admin = "admin"
    member = "member"


class Organization(Base):
    __tablename__ = "organizations"
    name: Mapped[str] = mapped_column(String(200))
    industry: Mapped[str] = mapped_column(String(100), default="general")
    settings: Mapped[dict] = mapped_column(JSON, default=dict)


class User(Base):
    __tablename__ = "users"
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(200))
    name: Mapped[str] = mapped_column(String(200), default="")


class Membership(Base):
    """User↔Organization link with a role (this is the roles table of the PRD)."""

    __tablename__ = "memberships"
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), index=True)
    role: Mapped[Role] = mapped_column(Enum(Role), default=Role.member)

    user: Mapped[User] = relationship(lazy="joined")


class Agent(Base):
    __tablename__ = "agents"
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    greeting: Mapped[str] = mapped_column(Text, default="Hello! How can I help you today?")
    system_prompt: Mapped[str] = mapped_column(Text, default="You are a helpful receptionist.")
    voice: Mapped[str] = mapped_column(String(100), default="kokoro-default")
    language: Mapped[str] = mapped_column(String(20), default="en-US")
    transfer_number: Mapped[str] = mapped_column(String(30), default="")
    # Transfer to a human once the caller finalizes (e.g. books an appointment).
    transfer_after_booking: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class PhoneNumber(Base):
    __tablename__ = "phone_numbers"
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), index=True)
    agent_id: Mapped[str | None] = mapped_column(ForeignKey("agents.id"), nullable=True)
    number: Mapped[str] = mapped_column(String(30), unique=True)
    provider: Mapped[str] = mapped_column(String(50), default="telnyx")


class KnowledgeBase(Base):
    __tablename__ = "knowledge_bases"
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), index=True)
    name: Mapped[str] = mapped_column(String(200), default="Default")


class Document(Base):
    __tablename__ = "documents"
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), index=True)
    knowledge_base_id: Mapped[str] = mapped_column(ForeignKey("knowledge_bases.id"), index=True)
    filename: Mapped[str] = mapped_column(String(500))
    content_type: Mapped[str] = mapped_column(String(100), default="text/plain")
    storage_key: Mapped[str] = mapped_column(String(500), default="")
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending|processing|ready|failed
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)


class DocumentChunk(Base):
    """Chunk text + vector id (the embeddings table; vectors live in Qdrant,
    this row doubles as a keyword-search fallback when Qdrant is down)."""

    __tablename__ = "document_chunks"
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), index=True)
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id"), index=True)
    position: Mapped[int] = mapped_column(Integer, default=0)
    content: Mapped[str] = mapped_column(Text)
    vector_id: Mapped[str] = mapped_column(String(36), default="")


class CallStatus(str, enum.Enum):
    ringing = "ringing"
    in_progress = "in_progress"
    completed = "completed"
    transferred = "transferred"
    failed = "failed"


class Call(Base):
    __tablename__ = "calls"
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), index=True)
    agent_id: Mapped[str | None] = mapped_column(ForeignKey("agents.id"), nullable=True)
    provider_call_id: Mapped[str] = mapped_column(String(200), default="", index=True)
    direction: Mapped[str] = mapped_column(String(10), default="inbound")
    caller_number: Mapped[str] = mapped_column(String(30), default="")
    caller_name: Mapped[str] = mapped_column(String(200), default="")  # collected during the call
    to_number: Mapped[str] = mapped_column(String(30), default="")
    status: Mapped[CallStatus] = mapped_column(Enum(CallStatus), default=CallStatus.ringing)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_seconds: Mapped[float] = mapped_column(Float, default=0)
    transferred_to: Mapped[str] = mapped_column(String(30), default="")
    # Storage key of the call audio, or an external URL (e.g. from Dograh/Telnyx).
    recording_key: Mapped[str] = mapped_column(String(600), default="")


class TranscriptTurn(Base):
    __tablename__ = "transcripts"
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), index=True)
    call_id: Mapped[str] = mapped_column(ForeignKey("calls.id"), index=True)
    position: Mapped[int] = mapped_column(Integer, default=0)
    role: Mapped[str] = mapped_column(String(20))  # caller | agent | system
    content: Mapped[str] = mapped_column(Text)


class Summary(Base):
    __tablename__ = "summaries"
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), index=True)
    call_id: Mapped[str] = mapped_column(ForeignKey("calls.id"), unique=True)
    content: Mapped[str] = mapped_column(Text)
    intent: Mapped[str] = mapped_column(String(100), default="")
    sentiment: Mapped[str] = mapped_column(String(20), default="neutral")


class Appointment(Base):
    __tablename__ = "appointments"
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), index=True)
    call_id: Mapped[str | None] = mapped_column(ForeignKey("calls.id"), nullable=True)
    contact_name: Mapped[str] = mapped_column(String(200), default="")
    contact_phone: Mapped[str] = mapped_column(String(30), default="")
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(20), default="booked")  # booked|cancelled|completed
    external_id: Mapped[str] = mapped_column(String(200), default="")  # calendar provider event id


class Integration(Base):
    __tablename__ = "integrations"
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), index=True)
    provider: Mapped[str] = mapped_column(String(50))  # google_calendar|outlook|hubspot|gohighlevel|telnyx|dograh
    config: Mapped[dict] = mapped_column(JSON, default=dict)  # non-secret config; secrets stay in env
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), index=True)
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    action: Mapped[str] = mapped_column(String(100))
    entity: Mapped[str] = mapped_column(String(100), default="")
    entity_id: Mapped[str] = mapped_column(String(36), default="")
    meta: Mapped[dict] = mapped_column(JSON, default=dict)
