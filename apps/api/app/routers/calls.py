from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.responses import RedirectResponse
from sqlalchemy import func, select

from app.deps import TenantCtx, get_ctx
from app.models import Agent, Call, Summary, TranscriptTurn
from app.providers.registry import get_storage
from app.schemas import CallDetailOut, CallOut, Page, SimulateIn
from app.services import voice

router = APIRouter(prefix="/calls", tags=["calls"])


@router.get("", response_model=Page)
async def list_calls(
    ctx: TenantCtx = Depends(get_ctx),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    base = select(Call).where(Call.organization_id == ctx.organization_id, Call.deleted_at.is_(None))
    total = (await ctx.db.execute(select(func.count()).select_from(base.subquery()))).scalar_one()
    rows = (await ctx.db.execute(base.order_by(Call.started_at.desc()).limit(limit).offset(offset))).scalars().all()
    return Page(total=total, items=[CallOut.model_validate(r).model_dump() for r in rows])


async def _get_call(ctx: TenantCtx, call_id: str) -> Call:
    call = await ctx.db.get(Call, call_id)
    if call is None or call.organization_id != ctx.organization_id or call.deleted_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Call not found")
    return call


@router.get("/{call_id}", response_model=CallDetailOut)
async def call_detail(call_id: str, ctx: TenantCtx = Depends(get_ctx)):
    call = await _get_call(ctx, call_id)
    turns = (
        await ctx.db.execute(
            select(TranscriptTurn).where(TranscriptTurn.call_id == call.id).order_by(TranscriptTurn.position)
        )
    ).scalars().all()
    summary = (await ctx.db.execute(select(Summary).where(Summary.call_id == call.id))).scalar_one_or_none()
    detail = CallDetailOut.model_validate(call)
    detail.turns = turns
    detail.summary = summary
    detail.has_recording = bool(call.recording_key)
    return detail


@router.get("/{call_id}/recording")
async def call_recording(call_id: str, ctx: TenantCtx = Depends(get_ctx)):
    """Call audio: streams from object storage, or redirects when the
    provider (Dograh/Telnyx) hosts the recording externally."""
    call = await _get_call(ctx, call_id)
    if not call.recording_key:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No recording for this call")
    if call.recording_key.startswith(("http://", "https://")):
        return RedirectResponse(call.recording_key)
    try:
        audio = await get_storage().get(call.recording_key)
    except FileNotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Recording file missing")
    return Response(content=audio, media_type="audio/wav",
                    headers={"Content-Disposition": f'inline; filename="call-{call.id}.wav"'})


@router.post("/simulate", response_model=CallDetailOut, status_code=201)
async def simulate(body: SimulateIn, ctx: TenantCtx = Depends(get_ctx)):
    """Run the full voice pipeline in-process with the configured providers.
    With mocks this needs no credentials — the end-to-end demo endpoint."""
    agent = await ctx.db.get(Agent, body.agent_id)
    if agent is None or agent.organization_id != ctx.organization_id or agent.deleted_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Agent not found")
    call = await voice.simulate_call(ctx.db, agent, body.caller_number, body.utterances)
    await ctx.db.commit()
    return await call_detail(call.id, ctx)
