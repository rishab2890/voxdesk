"""The voice conversation loop (mirrors the Dograh workflow spec):
greeting → collect caller → identify intent → knowledge lookup → tool call
→ transfer if required → summary → end call.

In production Dograh drives the realtime audio and calls back via webhooks;
`run_turn`/`finish_call` are the shared brain. `simulate_call` runs the whole
flow in-process on the mock providers so the pipeline is demoable and
testable with zero credentials."""

import logging
import re
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Agent, Appointment, Call, CallStatus, Summary, TranscriptTurn, utcnow
from app.providers.base import ChatMessage, TimeSlot
from app.providers.mock import BOOK_TOOL, TRANSFER_TOOL, concat_wavs
from app.providers.registry import get_calendar, get_crm, get_llm, get_stt, get_storage, get_telephony, get_tts
from app.services import rag

log = logging.getLogger(__name__)

# "Collect caller": pull the caller's name out of natural phrasing.
NAME_RE = re.compile(r"\b(?:my name is|this is|i am|i'm)\s+([a-z][a-z'-]+(?:\s[a-z][a-z'-]+)?)", re.IGNORECASE)


def extract_caller_name(text: str) -> str:
    match = NAME_RE.search(text)
    return match.group(1).title() if match else ""

TOOLS = [
    {"name": BOOK_TOOL, "description": "Book an appointment for the caller",
     "parameters": {"starts_at": "ISO datetime", "duration_min": "int"}},
    {"name": TRANSFER_TOOL, "description": "Transfer the call to a human", "parameters": {}},
]


async def _add_turn(db: AsyncSession, call: Call, role: str, content: str) -> None:
    position = (
        await db.execute(select(func.count()).select_from(TranscriptTurn).where(TranscriptTurn.call_id == call.id))
    ).scalar_one()
    db.add(TranscriptTurn(organization_id=call.organization_id, call_id=call.id,
                          position=position, role=role, content=content))
    await db.flush()


async def _history(db: AsyncSession, call: Call) -> list[ChatMessage]:
    turns = (
        await db.execute(
            select(TranscriptTurn).where(TranscriptTurn.call_id == call.id).order_by(TranscriptTurn.position)
        )
    ).scalars().all()
    role_map = {"caller": "user", "agent": "assistant"}
    return [ChatMessage(role=role_map.get(t.role, "system"), content=t.content) for t in turns]


async def start_call(db: AsyncSession, agent: Agent, caller_number: str, to_number: str = "",
                     provider_call_id: str = "") -> Call:
    call = Call(organization_id=agent.organization_id, agent_id=agent.id, caller_number=caller_number,
                to_number=to_number, provider_call_id=provider_call_id, status=CallStatus.in_progress)
    db.add(call)
    await db.flush()
    await _add_turn(db, call, "agent", agent.greeting)
    return call


async def run_turn(db: AsyncSession, call: Call, agent: Agent, audio: bytes) -> str:
    """One caller utterance through STT → RAG → LLM → tools → TTS. Returns the agent reply text."""
    text = await get_stt().transcribe(audio, language=agent.language)
    await _add_turn(db, call, "caller", text)

    if not call.caller_name:
        call.caller_name = extract_caller_name(text)

    context_chunks = await rag.retrieve(db, call.organization_id, text)
    messages = [ChatMessage(role="system", content=agent.system_prompt)]
    if context_chunks:
        joined = "\n".join(c["content"] for c in context_chunks)
        messages.append(ChatMessage(role="system", content=f"Context:\n{joined}"))
    messages += await _history(db, call)

    result = await get_llm().chat(messages, tools=TOOLS)

    booked = False
    for tool_call in result.tool_calls:
        if tool_call["name"] == BOOK_TOOL:
            args = tool_call["arguments"]
            starts = datetime.fromisoformat(args.get("starts_at")) if args.get("starts_at") \
                else datetime.now(timezone.utc) + timedelta(days=1)
            duration = int(args.get("duration_min", 30))
            slot = TimeSlot(starts_at=starts, ends_at=starts + timedelta(minutes=duration))
            contact = call.caller_name or "Caller"
            external_id = await get_calendar().book(slot, contact_name=contact, contact_phone=call.caller_number)
            await get_crm().upsert_contact(name=contact, phone=call.caller_number)
            db.add(Appointment(organization_id=call.organization_id, call_id=call.id,
                               contact_name=call.caller_name, contact_phone=call.caller_number,
                               starts_at=slot.starts_at, ends_at=slot.ends_at, external_id=external_id))
            booked = True
        elif tool_call["name"] == TRANSFER_TOOL and agent.transfer_number:
            await _transfer(call, agent)

    await _add_turn(db, call, "agent", result.content)
    await get_tts().synthesize(result.content, voice=agent.voice)  # audio returned to the engine in production

    # Finalization hand-off: once the caller books, route to a human to convert.
    if booked and agent.transfer_after_booking and agent.transfer_number \
            and call.status != CallStatus.transferred:
        await _transfer(call, agent)
        await _add_turn(db, call, "agent",
                        "I'll now connect you with a team member to finalize everything. One moment please.")

    return result.content


async def _transfer(call: Call, agent: Agent) -> None:
    if call.provider_call_id:
        await get_telephony().transfer_call(call.provider_call_id, agent.transfer_number)
    call.status = CallStatus.transferred
    call.transferred_to = agent.transfer_number


async def finish_call(db: AsyncSession, call: Call) -> Summary:
    call.ended_at = utcnow()
    call.duration_seconds = max((call.ended_at - call.started_at).total_seconds(), 0)
    if call.status == CallStatus.in_progress:
        call.status = CallStatus.completed

    history = await _history(db, call)
    result = await get_llm().chat(history + [ChatMessage(role="system", content="Summarize this call briefly.")])
    intent = "transfer" if call.status == CallStatus.transferred else "inquiry"
    summary = Summary(organization_id=call.organization_id, call_id=call.id, content=result.content, intent=intent)
    db.add(summary)

    await _store_recording(db, call, history)
    await db.flush()
    return summary


async def _store_recording(db: AsyncSession, call: Call, history: list[ChatMessage]) -> None:
    """Store the call audio. With a real engine, Dograh/Telnyx posts a
    recording URL on call.ended (see webhooks) and this is a no-op; otherwise
    we render the transcript through TTS so every call has playable audio."""
    if call.recording_key:
        return
    try:
        tts = get_tts()
        parts = [await tts.synthesize(m.content, voice="caller" if m.role == "user" else "agent")
                 for m in history if m.content]
        audio = concat_wavs(parts)
        if not audio:
            return
        key = f"{call.organization_id}/recordings/{call.id}.wav"
        await get_storage().put(key, audio)
        call.recording_key = key
    except Exception:
        log.warning("Could not render call recording for %s", call.id, exc_info=True)


async def simulate_call(db: AsyncSession, agent: Agent, caller_number: str, utterances: list[str]) -> Call:
    """Full pipeline in-process — the demo/testing entry point."""
    call = await start_call(db, agent, caller_number)
    for utterance in utterances:
        await run_turn(db, call, agent, utterance.encode())
        if call.status == CallStatus.transferred:
            break
    await finish_call(db, call)
    return call
