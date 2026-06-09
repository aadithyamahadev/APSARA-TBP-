from __future__ import annotations

from typing import Any

from fastapi import Request
from sqlalchemy import bindparam, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import AsyncSessionLocal


def get_request_ip(request: Request | None) -> str | None:
    if request is None:
        return None

    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        first_hop = forwarded_for.split(",", 1)[0].strip()
        if first_hop:
            return first_hop

    if request.client is not None:
        return request.client.host

    return None


async def write_audit_log(
    db: AsyncSession,
    *,
    action: str,
    user_id: str | None = None,
    ip_address: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    payload = metadata if isinstance(metadata, dict) else {}

    await db.execute(
        text(
            """
            INSERT INTO audit_logs (user_id, action, ip_address, metadata)
            VALUES (:user_id, :action, :ip_address, :metadata)
            """
        ).bindparams(bindparam("metadata", type_=JSONB)),
        {
            "user_id": user_id,
            "action": action,
            "ip_address": ip_address,
            "metadata": payload,
        },
    )


async def safe_write_audit_log(
    *,
    action: str,
    user_id: str | None = None,
    ip_address: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    try:
        async with AsyncSessionLocal() as db:
            await write_audit_log(
                db,
                action=action,
                user_id=user_id,
                ip_address=ip_address,
                metadata=metadata,
            )
            await db.commit()
    except Exception:
        # Never break request handling if audit persistence fails.
        return