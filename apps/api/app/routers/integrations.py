from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select

from app.deps import TenantCtx, audit, get_ctx, require_role
from app.models import Integration, Role
from app.schemas import IntegrationIn, IntegrationOut

router = APIRouter(prefix="/integrations", tags=["integrations"])

KNOWN_PROVIDERS = {"telnyx", "dograh", "google_calendar", "outlook", "hubspot", "gohighlevel", "webhook"}


@router.get("", response_model=list[IntegrationOut])
async def list_integrations(ctx: TenantCtx = Depends(get_ctx)):
    return (
        await ctx.db.execute(
            select(Integration).where(
                Integration.organization_id == ctx.organization_id, Integration.deleted_at.is_(None)
            )
        )
    ).scalars().all()


@router.put("/{provider}", response_model=IntegrationOut)
async def upsert_integration(provider: str, body: IntegrationIn,
                             ctx: TenantCtx = Depends(require_role(Role.owner, Role.admin))):
    if provider not in KNOWN_PROVIDERS:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, f"Known providers: {sorted(KNOWN_PROVIDERS)}")
    row = (
        await ctx.db.execute(
            select(Integration).where(
                Integration.organization_id == ctx.organization_id, Integration.provider == provider
            )
        )
    ).scalar_one_or_none()
    if row is None:
        row = Integration(organization_id=ctx.organization_id, provider=provider)
        ctx.db.add(row)
    row.config = body.config
    row.is_active = body.is_active
    row.deleted_at = None
    await audit(ctx, "integration.updated", "integration", provider)
    await ctx.db.commit()
    return row
