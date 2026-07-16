from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select

from app.deps import TenantCtx, audit, get_ctx, require_role
from app.models import Agent, PhoneNumber, Role, utcnow
from app.providers.registry import get_telephony, get_voice_engine
from app.schemas import AgentIn, AgentOut, PhoneNumberIn, PhoneNumberOut

router = APIRouter(prefix="/agents", tags=["agents"])


async def _get_agent(ctx: TenantCtx, agent_id: str) -> Agent:
    agent = await ctx.db.get(Agent, agent_id)
    if agent is None or agent.organization_id != ctx.organization_id or agent.deleted_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Agent not found")
    return agent


@router.get("", response_model=list[AgentOut])
async def list_agents(ctx: TenantCtx = Depends(get_ctx)):
    return (
        await ctx.db.execute(
            select(Agent).where(Agent.organization_id == ctx.organization_id, Agent.deleted_at.is_(None))
            .order_by(Agent.created_at)
        )
    ).scalars().all()


@router.post("", response_model=AgentOut, status_code=201)
async def create_agent(body: AgentIn, ctx: TenantCtx = Depends(require_role(Role.owner, Role.admin))):
    agent = Agent(organization_id=ctx.organization_id, **body.model_dump())
    ctx.db.add(agent)
    await ctx.db.flush()
    await get_voice_engine().sync_agent_workflow(agent.id, body.model_dump())
    await audit(ctx, "agent.created", "agent", agent.id)
    await ctx.db.commit()
    return agent


@router.get("/{agent_id}", response_model=AgentOut)
async def get_agent(agent_id: str, ctx: TenantCtx = Depends(get_ctx)):
    return await _get_agent(ctx, agent_id)


@router.put("/{agent_id}", response_model=AgentOut)
async def update_agent(agent_id: str, body: AgentIn, ctx: TenantCtx = Depends(require_role(Role.owner, Role.admin))):
    agent = await _get_agent(ctx, agent_id)
    for field, value in body.model_dump().items():
        setattr(agent, field, value)
    await get_voice_engine().sync_agent_workflow(agent.id, body.model_dump())
    await audit(ctx, "agent.updated", "agent", agent.id)
    await ctx.db.commit()
    return agent


@router.delete("/{agent_id}", status_code=204)
async def delete_agent(agent_id: str, ctx: TenantCtx = Depends(require_role(Role.owner, Role.admin))):
    agent = await _get_agent(ctx, agent_id)
    agent.deleted_at = utcnow()
    await audit(ctx, "agent.deleted", "agent", agent.id)
    await ctx.db.commit()


# ── Phone numbers ─────────────────────────────────────────────────────
numbers = APIRouter(prefix="/phone-numbers", tags=["phone-numbers"])


@numbers.get("", response_model=list[PhoneNumberOut])
async def list_numbers(ctx: TenantCtx = Depends(get_ctx)):
    return (
        await ctx.db.execute(
            select(PhoneNumber).where(
                PhoneNumber.organization_id == ctx.organization_id, PhoneNumber.deleted_at.is_(None)
            )
        )
    ).scalars().all()


@numbers.get("/available", response_model=list[str])
async def available_numbers(area_code: str = "", ctx: TenantCtx = Depends(get_ctx)):
    return await get_telephony().list_available_numbers(area_code)


@numbers.post("", response_model=PhoneNumberOut, status_code=201)
async def provision_number(body: PhoneNumberIn, ctx: TenantCtx = Depends(require_role(Role.owner, Role.admin))):
    if body.agent_id:
        await _get_agent(ctx, body.agent_id)
    await get_telephony().provision_number(body.number)
    row = PhoneNumber(organization_id=ctx.organization_id, number=body.number, agent_id=body.agent_id)
    ctx.db.add(row)
    await audit(ctx, "phone_number.provisioned", "phone_number", body.number)
    await ctx.db.commit()
    return row
