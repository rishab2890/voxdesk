from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import select

from app.deps import TenantCtx, get_ctx
from app.models import Appointment
from app.providers.registry import get_calendar
from app.schemas import AppointmentOut

router = APIRouter(prefix="/appointments", tags=["appointments"])


@router.get("", response_model=list[AppointmentOut])
async def list_appointments(ctx: TenantCtx = Depends(get_ctx)):
    return (
        await ctx.db.execute(
            select(Appointment).where(
                Appointment.organization_id == ctx.organization_id, Appointment.deleted_at.is_(None)
            ).order_by(Appointment.starts_at.desc())
        )
    ).scalars().all()


@router.get("/slots")
async def available_slots(day: datetime | None = None, ctx: TenantCtx = Depends(get_ctx)):
    slots = await get_calendar().list_slots(day or datetime.now(timezone.utc))
    return [{"starts_at": s.starts_at, "ends_at": s.ends_at} for s in slots]
