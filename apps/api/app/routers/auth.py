from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.deps import TenantCtx, get_ctx, rate_limit
from app.models import KnowledgeBase, Membership, Organization, Role, User
from app.schemas import LoginIn, RegisterIn, TokenOut, UserOut
from app.security import create_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"], dependencies=[Depends(rate_limit)])


@router.post("/register", response_model=TokenOut, status_code=201)
async def register(body: RegisterIn, db: AsyncSession = Depends(get_db)):
    existing = (await db.execute(select(User).where(User.email == body.email))).scalar_one_or_none()
    if existing:
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")

    user = User(email=body.email, password_hash=hash_password(body.password), name=body.name)
    org = Organization(name=body.organization_name, industry=body.industry)
    db.add_all([user, org])
    await db.flush()
    db.add(Membership(user_id=user.id, organization_id=org.id, role=Role.owner))
    db.add(KnowledgeBase(organization_id=org.id))  # default KB per org
    await db.commit()
    return TokenOut(access_token=create_token(user.id, org.id), organization_id=org.id)


@router.post("/login", response_model=TokenOut)
async def login(body: LoginIn, db: AsyncSession = Depends(get_db)):
    user = (await db.execute(select(User).where(User.email == body.email, User.deleted_at.is_(None)))).scalar_one_or_none()
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")
    membership = (
        await db.execute(
            select(Membership).where(Membership.user_id == user.id, Membership.deleted_at.is_(None))
        )
    ).scalars().first()
    if membership is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "No organization membership")
    return TokenOut(access_token=create_token(user.id, membership.organization_id),
                    organization_id=membership.organization_id)


@router.get("/me", response_model=UserOut)
async def me(ctx: TenantCtx = Depends(get_ctx)):
    return ctx.user
