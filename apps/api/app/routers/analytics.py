from sqlalchemy import func, select

from fastapi import APIRouter, Depends

from app.deps import TenantCtx, get_ctx
from app.models import Appointment, Call, CallStatus
from app.schemas import AnalyticsOut

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("", response_model=AnalyticsOut)
async def overview(ctx: TenantCtx = Depends(get_ctx)):
    db, org = ctx.db, ctx.organization_id
    calls = select(Call).where(Call.organization_id == org, Call.deleted_at.is_(None)).subquery()

    total = (await db.execute(select(func.count()).select_from(calls))).scalar_one()
    completed = (await db.execute(
        select(func.count()).select_from(calls).where(calls.c.status == CallStatus.completed))).scalar_one()
    transferred = (await db.execute(
        select(func.count()).select_from(calls).where(calls.c.status == CallStatus.transferred))).scalar_one()
    avg_duration = (await db.execute(select(func.avg(calls.c.duration_seconds)))).scalar_one() or 0
    appointments = (await db.execute(
        select(func.count()).select_from(Appointment).where(
            Appointment.organization_id == org, Appointment.deleted_at.is_(None)))).scalar_one()

    per_day_rows = (
        await db.execute(
            select(func.date(calls.c.started_at).label("day"), func.count().label("count"))
            .group_by("day").order_by("day")
        )
    ).all()

    return AnalyticsOut(
        total_calls=total,
        completed_calls=completed,
        transferred_calls=transferred,
        avg_duration_seconds=round(float(avg_duration), 1),
        appointments_booked=appointments,
        calls_per_day=[{"day": str(r.day), "count": r.count} for r in per_day_rows],
    )
