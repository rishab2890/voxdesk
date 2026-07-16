from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select

from app.deps import TenantCtx, audit, get_ctx, require_role
from app.models import Membership, Organization, Role, User
from app.schemas import InviteIn, MemberOut, OrgOut, OrgUpdate
from app.security import hash_password

router = APIRouter(prefix="/organizations", tags=["organizations"])


@router.get("/current", response_model=OrgOut)
async def current_org(ctx: TenantCtx = Depends(get_ctx)):
    return await ctx.db.get(Organization, ctx.organization_id)


@router.patch("/current", response_model=OrgOut)
async def update_org(body: OrgUpdate, ctx: TenantCtx = Depends(require_role(Role.owner, Role.admin))):
    org = await ctx.db.get(Organization, ctx.organization_id)
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(org, field, value)
    await audit(ctx, "organization.updated", "organization", org.id)
    await ctx.db.commit()
    return org


@router.get("/current/members", response_model=list[MemberOut])
async def list_members(ctx: TenantCtx = Depends(get_ctx)):
    rows = (
        await ctx.db.execute(
            select(Membership).where(
                Membership.organization_id == ctx.organization_id, Membership.deleted_at.is_(None)
            )
        )
    ).scalars().all()
    return [MemberOut(id=m.id, user=m.user, role=m.role.value) for m in rows]


@router.post("/current/members", response_model=MemberOut, status_code=201)
async def invite_member(body: InviteIn, ctx: TenantCtx = Depends(require_role(Role.owner, Role.admin))):
    # ponytail: creates the account directly; swap for email-invite flow when needed.
    if body.role not in (Role.admin.value, Role.member.value):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Role must be admin or member")
    user = (await ctx.db.execute(select(User).where(User.email == body.email))).scalar_one_or_none()
    if user is None:
        user = User(email=body.email, name=body.name, password_hash=hash_password(body.password))
        ctx.db.add(user)
        await ctx.db.flush()
    membership = Membership(user_id=user.id, organization_id=ctx.organization_id, role=Role(body.role))
    ctx.db.add(membership)
    await audit(ctx, "member.invited", "user", user.id, email=body.email)
    await ctx.db.commit()
    return MemberOut(id=membership.id, user=user, role=membership.role.value)
