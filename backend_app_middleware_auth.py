from typing import Any
import json
from uuid import UUID

from fastapi import Depends, Header, HTTPException, status
from jose import JWTError, jwt
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.dependencies import get_db_session
from app.redis_client import redis_client


async def get_current_user(
    authorization: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = authorization.split(" ", 1)[1].strip()
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    user_id = payload.get("sub")
    email = payload.get("email")
    username = payload.get("username")
    role = payload.get("role")
    jti = payload.get("jti")
    exp = payload.get("exp")

    if not isinstance(user_id, str) or not isinstance(jti, str) or not isinstance(exp, int):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )

    is_admin_token = role == "admin"
    if is_admin_token:
        if not isinstance(username, str):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid admin token payload",
                headers={"WWW-Authenticate": "Bearer"},
            )
    elif not isinstance(email, str):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        UUID(user_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token subject",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    blocked = await redis_client.get(f"blocklist:{jti}")
    if blocked is not None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token revoked",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        if is_admin_token:
            row = (
                (
                    await db.execute(
                        text(
                            """
                            SELECT id::text AS id, email, created_at
                            FROM admin_users
                            WHERE id = :user_id AND is_active = true
                            LIMIT 1
                            """
                        ),
                        {"user_id": user_id},
                    )
                )
                .mappings()
                .first()
            )
        else:
            row = (
                (
                    await db.execute(
                        text(
                            """
                            SELECT id::text AS id, email, created_at
                            FROM users
                            WHERE id = :user_id
                            LIMIT 1
                            """
                        ),
                        {"user_id": user_id},
                    )
                )
                .mappings()
                .first()
            )
    except Exception:
        row = None

    if row is None:
        fallback_raw = await redis_client.get(f"auth:user:id:{user_id}")
        if isinstance(fallback_raw, str) and fallback_raw:
            try:
                fallback_row = json.loads(fallback_raw)
            except json.JSONDecodeError:
                fallback_row = None

            if isinstance(fallback_row, dict):
                fallback_email = fallback_row.get("email")
                fallback_created_at = fallback_row.get("created_at")
                if isinstance(fallback_email, str) and isinstance(fallback_created_at, str):
                    return {
                        "id": str(fallback_row.get("id", user_id)),
                        "email": fallback_email,
                        "created_at": fallback_created_at,
                        "jti": jti,
                        "exp": exp,
                    }

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return {
        "id": row["id"],
        "email": row["email"],
        "username": username if isinstance(username, str) else None,
        "role": "admin" if is_admin_token else "user",
        "created_at": row["created_at"],
        "jti": jti,
        "exp": exp,
    }