"""Inbound provider webhooks (unauthenticated by design — verified by
provider signature once real credentials exist).

Telnyx events create/close call records. Dograh events carry the live
conversation: each caller utterance is routed through the shared voice
pipeline (RAG → LLM → tools) and the reply is returned in the response,
so the engine remains a thin, replaceable audio layer."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models import Agent, Call, CallStatus, PhoneNumber
from app.services import voice

log = logging.getLogger(__name__)
router = APIRouter(prefix="/webhooks", tags=["webhooks"])


def _verify_telnyx_signature(request: Request) -> None:
    # ponytail: signature check is a no-op with placeholder keys; wire
    # telnyx.webhooks Ed25519 verification when TELNYX_PUBLIC_KEY is real.
    return None


async def _call_by_provider_id(db: AsyncSession, provider_call_id: str) -> Call | None:
    return (
        await db.execute(select(Call).where(Call.provider_call_id == provider_call_id))
    ).scalar_one_or_none()


async def _agent_for_number(db: AsyncSession, to_number: str) -> Agent | None:
    number = (
        await db.execute(select(PhoneNumber).where(PhoneNumber.number == to_number, PhoneNumber.deleted_at.is_(None)))
    ).scalar_one_or_none()
    if number is None or number.agent_id is None:
        return None
    return await db.get(Agent, number.agent_id)


@router.post("/telnyx")
async def telnyx_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    _verify_telnyx_signature(request)
    event = await request.json()
    data = event.get("data", {})
    event_type = data.get("event_type", "")
    payload = data.get("payload", {})
    provider_call_id = payload.get("call_control_id", "")

    if event_type == "call.initiated":
        agent = await _agent_for_number(db, payload.get("to", ""))
        if agent is None:
            log.warning("Inbound call to unmapped number %s", payload.get("to"))
            return {"ok": False, "reason": "no agent for number"}
        call = await voice.start_call(db, agent, caller_number=payload.get("from", ""),
                                      to_number=payload.get("to", ""), provider_call_id=provider_call_id)
        await db.commit()
        return {"ok": True, "call_id": call.id}

    if event_type == "call.hangup":
        call = await _call_by_provider_id(db, provider_call_id)
        if call and call.ended_at is None:
            await voice.finish_call(db, call)
            await db.commit()
        return {"ok": True}

    return {"ok": True, "ignored": event_type}


@router.post("/dograh")
async def dograh_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    event = await request.json()
    event_type = event.get("type", "")
    provider_call_id = event.get("call_id", "")

    call = await _call_by_provider_id(db, provider_call_id)
    if call is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Unknown call")
    agent = await db.get(Agent, call.agent_id)

    if event_type == "utterance":
        reply = await voice.run_turn(db, call, agent, event.get("text", "").encode())
        await db.commit()
        return {"ok": True, "reply": reply, "status": call.status.value}

    if event_type == "call.ended":
        # Engine-hosted recording wins over our TTS-rendered fallback.
        if event.get("recording_url"):
            call.recording_key = event["recording_url"]
        if call.ended_at is None:
            await voice.finish_call(db, call)
        await db.commit()
        return {"ok": True}

    return {"ok": True, "ignored": event_type}
