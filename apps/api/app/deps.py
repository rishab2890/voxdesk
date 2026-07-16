"""Auth + tenancy dependencies. Every org-scoped router uses TenantCtx,
which guarantees queries are filtered by the caller's organization_id."""

from dataclasses import dataclass

import jwt as pyjwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models import AuditLog, Membership, Role, User
from app.security import decode_token

bearer = HTTPBearer(auto_error=False)


@dataclass
class TenantCtx:
    user: User
    organization_id: str
    role: Role
    db: AsyncSession


async def get_ctx(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: AsyncSession = Depends(get_db),
) -> TenantCtx:
    if creds is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing bearer token")
    try:
        payload = decode_token(creds.credentials)
    except pyjwt.PyJWTError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token")

    user = await db.get(User, payload["sub"])
    if user is None or user.deleted_at is not None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Unknown user")

    membership = (
        await db.execute(
            select(Membership).where(
                Membership.user_id == user.id,
                Membership.organization_id == payload["org"],
                Membership.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if membership is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "No access to this organization")

    return TenantCtx(user=user, organization_id=payload["org"], role=membership.role, db=db)


def require_role(*roles: Role):
    async def checker(ctx: TenantCtx = Depends(get_ctx)) -> TenantCtx:
        if ctx.role not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, f"Requires role: {[r.value for r in roles]}")
        return ctx

    return checker


async def audit(ctx: TenantCtx, action: str, entity: str = "", entity_id: str = "", **meta) -> None:
    ctx.db.add(
        AuditLog(
            organization_id=ctx.organization_id,
            user_id=ctx.user.id,
            action=action,
            entity=entity,
            entity_id=entity_id,
            meta=meta,
        )
    )


async def rate_limit(request: Request) -> None:
    """Fixed-window limiter on Redis for unauthenticated endpoints.
    ponytail: fails open when Redis is unreachable; move to a gateway limiter at scale."""
    from app.redis_client import get_redis

    r = get_redis()
    if r is None:
        return
    key = f"rl:{request.client.host if request.client else 'unknown'}:{request.url.path}"
    try:
        count = await r.incr(key)
        if count == 1:
            await r.expire(key, 60)
        if count > 30:
            raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Too many requests")
    except HTTPException:
        raise
    except Exception:
        return
