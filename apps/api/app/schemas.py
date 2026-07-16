from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ── Auth ──────────────────────────────────────────────────────────────
class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    name: str = Field(min_length=1, max_length=200)
    organization_name: str = Field(min_length=1, max_length=200)
    industry: str = "general"


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    organization_id: str


class UserOut(ORMModel):
    id: str
    email: str
    name: str


# ── Organizations ─────────────────────────────────────────────────────
class OrgOut(ORMModel):
    id: str
    name: str
    industry: str
    settings: dict


class OrgUpdate(BaseModel):
    name: str | None = None
    industry: str | None = None
    settings: dict | None = None


class MemberOut(ORMModel):
    id: str
    user: UserOut
    role: str


class InviteIn(BaseModel):
    email: EmailStr
    name: str = ""
    password: str = Field(min_length=8, max_length=128)
    role: str = "member"


# ── Agents ────────────────────────────────────────────────────────────
class AgentIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    greeting: str = "Hello! How can I help you today?"
    system_prompt: str = "You are a helpful receptionist."
    voice: str = "kokoro-default"
    language: str = "en-US"
    transfer_number: str = ""
    transfer_after_booking: bool = False
    is_active: bool = True


class AgentOut(ORMModel, AgentIn):
    id: str
    created_at: datetime


# ── Phone numbers ─────────────────────────────────────────────────────
class PhoneNumberIn(BaseModel):
    number: str = Field(min_length=5, max_length=30)
    agent_id: str | None = None


class PhoneNumberOut(ORMModel):
    id: str
    number: str
    agent_id: str | None
    provider: str


# ── Knowledge base ────────────────────────────────────────────────────
class DocumentOut(ORMModel):
    id: str
    filename: str
    content_type: str
    status: str
    chunk_count: int
    created_at: datetime


class RetrieveIn(BaseModel):
    query: str = Field(min_length=1)
    top_k: int = Field(default=4, ge=1, le=20)


class RetrievedChunk(BaseModel):
    content: str
    document_id: str
    score: float


# ── Calls ─────────────────────────────────────────────────────────────
class TurnOut(ORMModel):
    position: int
    role: str
    content: str


class SummaryOut(ORMModel):
    content: str
    intent: str
    sentiment: str


class CallOut(ORMModel):
    id: str
    agent_id: str | None
    direction: str
    caller_number: str
    caller_name: str
    to_number: str
    status: str
    started_at: datetime
    ended_at: datetime | None
    duration_seconds: float
    transferred_to: str


class CallDetailOut(CallOut):
    turns: list[TurnOut] = []
    summary: SummaryOut | None = None
    has_recording: bool = False


class SimulateIn(BaseModel):
    agent_id: str
    caller_number: str = "+15550001234"
    utterances: list[str] = Field(min_length=1, max_length=20)


# ── Appointments ──────────────────────────────────────────────────────
class AppointmentOut(ORMModel):
    id: str
    call_id: str | None
    contact_name: str
    contact_phone: str
    starts_at: datetime
    ends_at: datetime
    status: str


# ── Integrations ──────────────────────────────────────────────────────
class IntegrationIn(BaseModel):
    provider: str
    config: dict = {}
    is_active: bool = False


class IntegrationOut(ORMModel, IntegrationIn):
    id: str


# ── Analytics ─────────────────────────────────────────────────────────
class AnalyticsOut(BaseModel):
    total_calls: int
    completed_calls: int
    transferred_calls: int
    avg_duration_seconds: float
    appointments_booked: int
    calls_per_day: list[dict]


class Page(BaseModel):
    total: int
    items: list
