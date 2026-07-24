"""Import finished Dograh call runs into VoxDesk calls/transcripts/summaries.

Called on demand (POST /calls/sync). For each Dograh workflow, new completed
runs are pulled and turned into Call + TranscriptTurn + Summary rows, with the
recording stored as Dograh's public URL (the /calls/{id}/recording endpoint
redirects to it). Idempotent via provider_call_id = "dograh-<run_id>".

ponytail: one Dograh instance serves the whole deployment, so a sync pulls
every workflow's runs into the requesting org. Fine for a single real tenant;
add per-org Dograh credentials when you go truly multi-tenant."""

import logging
import re

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Agent, Call, CallStatus, Summary, TranscriptTurn, utcnow
from app.providers.dograh import DograhVoiceEngine
from app.services.voice import extract_caller_name

log = logging.getLogger(__name__)

# Transcript lines look like: "[2026-07-24T13:13:18.654+00:00] assistant: text"
LINE_RE = re.compile(r"^\[(?P<ts>[^\]]+)\]\s*(?P<role>\w+):\s*(?P<content>.*)$")
ROLE_MAP = {"assistant": "agent", "user": "caller", "system": "system"}
TRANSFER_TAGS = {"transfer", "transferred", "human_transfer", "agent_transfer"}


def parse_transcript(text: str) -> list[tuple[str, str]]:
    """[(role, content)] with multi-line entries folded into the prior turn."""
    turns: list[list[str]] = []
    for line in text.splitlines():
        m = LINE_RE.match(line)
        if m:
            turns.append([ROLE_MAP.get(m["role"].lower(), "system"), m["content"].strip()])
        elif turns and line.strip():
            turns[-1][1] += " " + line.strip()
    return [(r, c) for r, c in turns if c]


async def _existing_ids(db: AsyncSession, organization_id: str) -> set[str]:
    rows = (
        await db.execute(
            select(Call.provider_call_id).where(
                Call.organization_id == organization_id, Call.provider_call_id.like("dograh-%")
            )
        )
    ).scalars().all()
    return set(rows)


async def sync_org(db: AsyncSession, organization_id: str) -> int:
    """Import new Dograh runs for this org. Returns how many calls were added."""
    engine = DograhVoiceEngine()
    if not await engine.health():
        raise RuntimeError("Dograh is not reachable (check DOGRAH_URL / DOGRAH_API_KEY)")

    # Map Dograh workflow name → VoxDesk agent (whitespace-insensitive).
    agents = (
        await db.execute(
            select(Agent).where(Agent.organization_id == organization_id, Agent.deleted_at.is_(None))
        )
    ).scalars().all()
    agent_by_name = {" ".join(a.name.split()).lower(): a for a in agents}

    already = await _existing_ids(db, organization_id)
    added = 0

    for wf in await engine.list_workflows():
        wf_id = wf.get("id") or wf.get("uuid")
        agent = agent_by_name.get(" ".join(str(wf.get("name", "")).split()).lower())
        for run in await engine.list_runs(wf_id):
            if not run.get("is_completed"):
                continue
            pcid = f"dograh-{run.get('id')}"
            if pcid in already:
                continue

            detail = await engine.get_run(wf_id, run["id"])
            turns = []
            if detail.get("transcript_public_url"):
                try:
                    turns = parse_transcript(await engine.fetch_transcript(detail["transcript_public_url"]))
                except Exception:
                    log.warning("Could not fetch transcript for run %s", run["id"], exc_info=True)

            ctx = detail.get("gathered_context") or {}
            tags = {str(t).lower() for t in ctx.get("call_tags", [])}
            disposition = ctx.get("call_disposition") or ctx.get("mapped_call_disposition") or ""
            transferred = bool(tags & TRANSFER_TAGS) or "transfer" in disposition.lower()
            duration = float((detail.get("cost_info") or {}).get("call_duration_seconds") or 0)
            caller_name = ""
            for role, content in turns:
                if role == "caller" and (name := extract_caller_name(content)):
                    caller_name = name
                    break

            call = Call(
                organization_id=organization_id,
                agent_id=agent.id if agent else None,
                provider_call_id=pcid,
                direction=detail.get("call_type", "inbound"),
                caller_name=caller_name,
                caller_number=detail.get("from_number", "") or detail.get("caller_number", ""),
                status=CallStatus.transferred if transferred else CallStatus.completed,
                duration_seconds=duration,
                ended_at=utcnow(),
                recording_key=detail.get("recording_public_url", "") or "",
            )
            db.add(call)
            await db.flush()

            for i, (role, content) in enumerate(turns):
                db.add(TranscriptTurn(organization_id=organization_id, call_id=call.id,
                                      position=i, role=role, content=content))

            n_caller = sum(1 for r, _ in turns if r == "caller")
            summary_text = (
                f"Imported from Dograh. {len(turns)} turns ({n_caller} from caller), "
                f"{duration:.0f}s. Disposition: {disposition or 'n/a'}."
            )
            db.add(Summary(organization_id=organization_id, call_id=call.id, content=summary_text,
                           intent="transfer" if transferred else "inquiry"))
            added += 1

    await db.commit()
    log.info("Dograh sync for org %s imported %d calls", organization_id, added)
    return added
