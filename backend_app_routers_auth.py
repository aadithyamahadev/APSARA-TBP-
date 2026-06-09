from datetime import datetime, timedelta, timezone
import json
from uuid import NAMESPACE_URL, uuid4, uuid5

import bcrypt
from fastapi import APIRouter, Depends, HTTPException, Request, status
from jose import jwt
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.dependencies import get_db_session
from app.middleware.auth import get_current_user
from app.models.schemas import LoginRequest, RegisterRequest, TokenResponse, UserResponse
from app.redis_client import redis_client
from app.services.audit import get_request_ip, safe_write_audit_log

router = APIRouter(prefix="/auth", tags=["auth"])


def _fallback_user_id(email: str) -> str:
    normalized_email = email.lower().strip()
    return str(uuid5(NAMESPACE_URL, f"apsara-auth:{normalized_email}"))


def _fallback_user_key(email: str) -> str:
    return f"auth:user:email:{email.lower().strip()}"


def _fallback_user_id_key(user_id: str) -> str:
    return f"auth:user:id:{user_id}"


async def _store_fallback_user(*, email: str, password: str, user_id: str | None = None) -> dict[str, str]:
    normalized_email = email.lower().strip()
    resolved_user_id = user_id or _fallback_user_id(normalized_email)
    created_at = datetime.now(timezone.utc).isoformat()
    hashed_password = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    record = {
        "id": resolved_user_id,
        "email": normalized_email,
        "hashed_password": hashed_password,
        "created_at": created_at,
    }
    payload = json.dumps(record)
    await redis_client.set(_fallback_user_key(normalized_email), payload)
    await redis_client.set(_fallback_user_id_key(resolved_user_id), payload)
    return record


async def _load_fallback_user_by_email(email: str) -> dict[str, str] | None:
    raw_value = await redis_client.get(_fallback_user_key(email))
    if not isinstance(raw_value, str) or not raw_value:
        return None

    try:
        parsed = json.loads(raw_value)
    except json.JSONDecodeError:
        return None

    if not isinstance(parsed, dict):
        return None

    return {
        "id": str(parsed.get("id", "")),
        "email": str(parsed.get("email", email.lower().strip())),
        "hashed_password": str(parsed.get("hashed_password", "")),
        "created_at": str(parsed.get("created_at", datetime.now(timezone.utc).isoformat())),
    }


def _issue_access_token(user_id: str, email: str) -> TokenResponse:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    expires_delta = timedelta(minutes=settings.jwt_expire_minutes)
    expires_at = now + expires_delta
    token_payload = {
        "sub": user_id,
        "email": email,
        "jti": str(uuid4()),
        "exp": expires_at,
    }
    encoded_jwt = jwt.encode(token_payload, settings.jwt_secret, algorithm="HS256")
    return TokenResponse(
        access_token=encoded_jwt,
        token_type="bearer",
        expires_in=int(expires_delta.total_seconds()),
    )


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    payload: RegisterRequest,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
) -> TokenResponse:
    normalized_email = payload.email.lower().strip()
    hashed_password = bcrypt.hashpw(payload.password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    try:
        row = (
            (
                await db.execute(
                    text(
                        """
                        INSERT INTO users (email, hashed_password)
                        VALUES (:email, :hashed_password)
                        RETURNING id::text AS id, email
                        """
                    ),
                    {"email": normalized_email, "hashed_password": hashed_password},
                )
            )
            .mappings()
            .first()
        )
        if row is None:
            raise SQLAlchemyError("user insert returned no row")
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        ) from exc
    except Exception:
        fallback_row = await _load_fallback_user_by_email(normalized_email)
        if fallback_row is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered",
            )

        fallback_row = await _store_fallback_user(
            email=normalized_email,
            password=payload.password,
        )
        await safe_write_audit_log(
            action="user_registered",
            user_id=fallback_row["id"],
            ip_address=get_request_ip(request),
            metadata={"email": fallback_row["email"], "mode": "fallback"},
        )
        return _issue_access_token(user_id=fallback_row["id"], email=fallback_row["email"])

    await safe_write_audit_log(
        action="user_registered",
        user_id=row["id"],
        ip_address=get_request_ip(request),
        metadata={"email": row["email"], "mode": "database"},
    )

    return _issue_access_token(user_id=row["id"], email=row["email"])


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
) -> TokenResponse:
    normalized_email = payload.email.lower().strip()
    fallback_mode = False

    try:
        row = (
            (
                await db.execute(
                    text(
                        """
                        SELECT id::text AS id, email, hashed_password
                        FROM users
                        WHERE email = :email
                        LIMIT 1
                        """
                    ),
                    {"email": normalized_email},
                )
            )
            .mappings()
            .first()
        )
    except Exception:
        fallback_mode = True
        row = await _load_fallback_user_by_email(normalized_email)
        if row is None:
            await safe_write_audit_log(
                action="user_login_failed",
                ip_address=get_request_ip(request),
                metadata={"email": normalized_email, "mode": "fallback"},
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

    valid_password = False
    if row is not None:
        valid_password = bcrypt.checkpw(
            payload.password.encode("utf-8"),
            row["hashed_password"].encode("utf-8"),
        )

    if row is None or not valid_password:
        await safe_write_audit_log(
            action="user_login_failed",
            user_id=row["id"] if row is not None else None,
            ip_address=get_request_ip(request),
            metadata={"email": normalized_email, "mode": "fallback" if row is None else "database"},
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    await safe_write_audit_log(
        action="user_login_success",
        user_id=row["id"],
        ip_address=get_request_ip(request),
        metadata={"email": row["email"], "mode": "fallback" if fallback_mode else "database"},
    )

    return _issue_access_token(user_id=row["id"], email=row["email"])


@router.get("/me", response_model=UserResponse)
async def me(current_user: dict = Depends(get_current_user)) -> UserResponse:
    return UserResponse(
        id=current_user["id"],
        email=current_user["email"],
        created_at=current_user["created_at"],
    )


@router.post("/logout")
async def logout(current_user: dict = Depends(get_current_user)) -> dict[str, str]:
    now_ts = int(datetime.now(timezone.utc).timestamp())
    ttl_seconds = int(current_user["exp"]) - now_ts
    if ttl_seconds <= 0:
        ttl_seconds = 1

    await redis_client.set(f"blocklist:{current_user['jti']}", "1", expire_seconds=ttl_seconds)
    return {"message": "Logged out"}