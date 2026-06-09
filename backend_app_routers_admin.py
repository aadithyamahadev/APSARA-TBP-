from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

import bcrypt
import hashlib
from fastapi import APIRouter, Depends, HTTPException, Query, status
from jose import jwt
from sqlalchemy import bindparam, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from zxcvbn import zxcvbn
from app.routers.breach import _extract_breach_count, _fetch_hibp_range_payload

from app.core.config import get_settings
from app.dependencies import get_db_session
from app.db import AsyncSessionLocal
from app.middleware.auth import get_current_user
from app.models.schemas import (
    AdminLoginRequest,
    AdminRegisterRequest,
    AuditLogListResponse,
    AuditLogRowResponse,
    PolicyRowResponse,
    PolicyUpdateRequest,
)
from app.services.policy_service import (
    DEFAULT_SERVICE_ID,
    PolicyValidationError,
    get_default_policy_value,
    invalidate_policy_cache,
    validate_policy_value,
)

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/audit-logs", response_model=AuditLogListResponse)
async def list_audit_logs(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    _: dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> AuditLogListResponse:
    offset = (page - 1) * page_size

    total_row = (
        (
            await db.execute(
                text(
                    """
                    SELECT COUNT(*)::bigint AS total
                    FROM audit_logs
                    """
                )
            )
        )
        .mappings()
        .first()
    )
    total = int(total_row["total"]) if total_row is not None else 0

    rows = (
        (
            await db.execute(
                text(
                    """
                    SELECT id, user_id, action, ip_address, metadata, created_at
                    FROM audit_logs
                    ORDER BY created_at DESC
                    LIMIT :limit_rows
                    OFFSET :offset_rows
                    """
                ),
                {"limit_rows": page_size, "offset_rows": offset},
            )
        )
        .mappings()
        .all()
    )

    return AuditLogListResponse(
        page=page,
        page_size=page_size,
        total=total,
        items=[
            AuditLogRowResponse(
                id=row["id"],
                user_id=row["user_id"],
                action=row["action"],
                ip_address=row["ip_address"],
                metadata=row["metadata"],
                created_at=row["created_at"],
            )
            for row in rows
        ],
    )


@router.get("/policies", response_model=list[PolicyRowResponse])
async def list_policies(
    service_id: str = Query(default=DEFAULT_SERVICE_ID, min_length=1, max_length=128),
    _: dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> list[PolicyRowResponse]:
    rows = (
        (
            await db.execute(
                text(
                    """
                    SELECT service_id, name, value, description, updated_by, updated_at
                    FROM policy_configs
                    WHERE service_id = :service_id
                    ORDER BY name
                    """
                ),
                {"service_id": service_id.strip() or DEFAULT_SERVICE_ID},
            )
        )
        .mappings()
        .all()
    )

    return [
        PolicyRowResponse(
            service_id=row["service_id"],
            name=row["name"],
            value=row["value"],
            description=row["description"],
            updated_by=row["updated_by"],
            updated_at=row["updated_at"],
        )
        for row in rows
    ]


@router.get("/policies/{name}", response_model=PolicyRowResponse)
async def get_policy(
    name: str,
    service_id: str = Query(default=DEFAULT_SERVICE_ID, min_length=1, max_length=128),
    _: dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> PolicyRowResponse:
    row = (
        (
            await db.execute(
                text(
                    """
                    SELECT service_id, name, value, description, updated_by, updated_at
                    FROM policy_configs
                    WHERE service_id = :service_id AND name = :name
                    LIMIT 1
                    """
                ),
                {
                    "service_id": service_id.strip() or DEFAULT_SERVICE_ID,
                    "name": name,
                },
            )
        )
        .mappings()
        .first()
    )

    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Policy not found")

    return PolicyRowResponse(
        service_id=row["service_id"],
        name=row["name"],
        value=row["value"],
        description=row["description"],
        updated_by=row["updated_by"],
        updated_at=row["updated_at"],
    )


@router.put("/policies/{name}", response_model=PolicyRowResponse)
async def update_policy(
    name: str,
    payload: PolicyUpdateRequest,
    current_user: dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> PolicyRowResponse:
    normalized_service_id = payload.service_id.strip() or DEFAULT_SERVICE_ID

    try:
        validated_value = validate_policy_value(name, payload.value)
    except PolicyValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    # Preserve description from default row when creating policy row for a new service.
    default_description_row = (
        (
            await db.execute(
                text(
                    """
                    SELECT description
                    FROM policy_configs
                    WHERE service_id = :service_id AND name = :name
                    LIMIT 1
                    """
                ),
                {"service_id": DEFAULT_SERVICE_ID, "name": name},
            )
        )
        .mappings()
        .first()
    )

    if default_description_row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Policy not found")

    row = (
        (
            await db.execute(
                text(
                    """
                    INSERT INTO policy_configs (service_id, name, value, description, updated_by, updated_at)
                    VALUES (:service_id, :name, :value, :description, :updated_by, now())
                    ON CONFLICT (service_id, name)
                    DO UPDATE SET
                        value = EXCLUDED.value,
                        updated_by = EXCLUDED.updated_by,
                        updated_at = now()
                    RETURNING service_id, name, value, description, updated_by, updated_at
                    """
                ).bindparams(bindparam("value", type_=JSONB)),
                {
                    "service_id": normalized_service_id,
                    "name": name,
                    "value": validated_value,
                    "description": default_description_row["description"],
                    "updated_by": current_user["id"],
                },
            )
        )
        .mappings()
        .first()
    )

    if row is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update policy")

    await db.commit()
    await invalidate_policy_cache(normalized_service_id, name)

    return PolicyRowResponse(
        service_id=row["service_id"],
        name=row["name"],
        value=row["value"],
        description=row["description"],
        updated_by=row["updated_by"],
        updated_at=row["updated_at"],
    )


@router.post("/policies/reset/{name}", response_model=PolicyRowResponse)
async def reset_policy(
    name: str,
    service_id: str = Query(default=DEFAULT_SERVICE_ID, min_length=1, max_length=128),
    current_user: dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> PolicyRowResponse:
    normalized_service_id = service_id.strip() or DEFAULT_SERVICE_ID

    try:
        default_value = get_default_policy_value(name)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Policy not found") from exc

    row = (
        (
            await db.execute(
                text(
                    """
                    INSERT INTO policy_configs (service_id, name, value, updated_by, updated_at)
                    VALUES (:service_id, :name, :value, :updated_by, now())
                    ON CONFLICT (service_id, name)
                    DO UPDATE SET
                        value = EXCLUDED.value,
                        updated_by = EXCLUDED.updated_by,
                        updated_at = now()
                    RETURNING service_id, name, value, description, updated_by, updated_at
                    """
                ).bindparams(bindparam("value", type_=JSONB)),
                {
                    "service_id": normalized_service_id,
                    "name": name,
                    "value": default_value,
                    "updated_by": current_user["id"],
                },
            )
        )
        .mappings()
        .first()
    )

    await db.commit()
    await invalidate_policy_cache(normalized_service_id, name)

    if row is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to reset policy")

    return PolicyRowResponse(
        service_id=row["service_id"],
        name=row["name"],
        value=row["value"],
        description=row["description"],
        updated_by=row["updated_by"],
        updated_at=row["updated_at"],
    )


# Admin Authentication and Dashboard Endpoints

@router.post("/auth/login", response_model=dict[str, Any])
async def admin_login(
    credentials: AdminLoginRequest,
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Admin login endpoint"""
    identifier = credentials.username.strip()
    row = (
        (
            await db.execute(
                text(
                    """
                    SELECT id::text AS id, username, hashed_password
                    FROM admin_users
                    WHERE lower(username) = lower(:identifier)
                       OR lower(email) = lower(:identifier)
                    LIMIT 1
                    """
                ),
                {"identifier": identifier},
            )
        )
        .mappings()
        .first()
    )

    if not row:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin credentials",
        )

    # Verify password
    if not bcrypt.checkpw(credentials.password.encode("utf-8"), row["hashed_password"].encode("utf-8")):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin credentials",
        )

    # Issue token
    settings = get_settings()
    now = datetime.now(timezone.utc)
    expires_delta = timedelta(minutes=settings.jwt_expire_minutes)
    expires_at = now + expires_delta
    token_payload = {
        "sub": row["id"],
        "username": row["username"],
        "role": "admin",
        "jti": str(uuid4()),
        "exp": expires_at,
    }
    encoded_jwt = jwt.encode(token_payload, settings.jwt_secret, algorithm="HS256")

    return {
        "access_token": encoded_jwt,
        "token_type": "bearer",
        "expires_in": int(expires_delta.total_seconds()),
        "admin_id": row["id"],
    }


@router.post("/auth/register-initial")
async def register_initial_admin(
    payload: AdminRegisterRequest,
) -> dict[str, str]:
    """Register the first admin user (only when no admins exist)"""
    password = payload.password
    
    # Enforce strict password requirements for admin accounts
    # 1. Minimum length requirement
    if len(password) < 12:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Admin password must be at least 12 characters long.",
        )
    
    # 2. Must contain at least one uppercase letter
    if not any(char.isupper() for char in password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Admin password must contain at least one uppercase letter.",
        )
    
    # 3. Must contain at least one lowercase letter
    if not any(char.islower() for char in password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Admin password must contain at least one lowercase letter.",
        )
    
    # 4. Must contain at least one digit
    if not any(char.isdigit() for char in password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Admin password must contain at least one digit.",
        )
    
    # 5. Must contain at least one special character
    if all(char.isalnum() for char in password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Admin password must contain at least one special character.",
        )

    # Check password strength using zxcvbn
    zxcvbn_result = zxcvbn(password)
    if zxcvbn_result.get("score", 0) < 3:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Admin password is too weak. Must have a strength score of at least 3 out of 4.",
        )

    # Check if password is breached in HIBP
    try:
        full_hash = hashlib.sha1(password.encode()).hexdigest().upper()
        prefix = full_hash[:5]
        suffix = full_hash[5:]
        hibp_payload = await _fetch_hibp_range_payload(prefix)
        breach_count = _extract_breach_count(hibp_payload, suffix)
        if breach_count > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Admin password was found in {breach_count} data breaches. Choose a different password.",
            )
    except HTTPException:
        raise
    except Exception:
        # Proceed if HIBP service itself fails/is down
        pass

    async with AsyncSessionLocal() as db:
        # Check if any admin exists
        existing = (await db.execute(text("SELECT COUNT(*) as count FROM admin_users"))).first()
        count = existing[0] if existing else 0

        if count > 0:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin user already exists",
            )

        hashed = bcrypt.hashpw(payload.password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
        await db.execute(
            text("""
                INSERT INTO admin_users (username, email, hashed_password, is_active)
                VALUES (:username, :email, :hashed_password, true)
            """),
            {"username": payload.username, "email": payload.email, "hashed_password": hashed},
        )
        await db.commit()

        return {"message": "Admin user created successfully"}


@router.get("/dashboard/metrics")
async def get_dashboard_metrics(
    current_user: dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Get password strength analytics"""

    # Total checks
    total = (await db.execute(text("SELECT COUNT(*) as total FROM password_checks"))).first()
    total_count = total[0] if total else 0

    # Strength distribution
    strength_dist = (
        await db.execute(
            text("""
                SELECT strength_label, COUNT(*) as count
                FROM password_checks
                GROUP BY strength_label
                ORDER BY count DESC
            """)
        )
    ).fetchall()
    strength_data = {row[0]: row[1] for row in strength_dist}

    # Risk distribution
    risk_dist = (
        await db.execute(
            text("""
                SELECT risk_label, COUNT(*) as count
                FROM password_checks
                GROUP BY risk_label
                ORDER BY count DESC
            """)
        )
    ).fetchall()
    risk_data = {row[0]: row[1] for row in risk_dist}

    # Breached count
    breached = (
        await db.execute(text("SELECT COUNT(*) FROM password_checks WHERE is_breached = true"))
    ).first()
    breached_count = breached[0] if breached else 0

    # Average score
    avg_score = (
        await db.execute(text("SELECT AVG(score) as avg_score FROM password_checks"))
    ).first()
    avg_score_val = float(avg_score[0]) if avg_score and avg_score[0] else 0

    # Score distribution (for chart)
    score_ranges = {
        "0-20": 0,
        "21-40": 0,
        "41-60": 0,
        "61-80": 0,
        "81-100": 0,
    }
    score_dist = (
        await db.execute(
            text("""
                SELECT
                    CASE
                        WHEN score <= 20 THEN '0-20'
                        WHEN score <= 40 THEN '21-40'
                        WHEN score <= 60 THEN '41-60'
                        WHEN score <= 80 THEN '61-80'
                        ELSE '81-100'
                    END as range,
                    COUNT(*) as count
                FROM password_checks
                GROUP BY range
            """)
        )
    ).fetchall()
    for row in score_dist:
        score_ranges[row[0]] = row[1]

    return {
        "total_checks": total_count,
        "strength_distribution": strength_data,
        "risk_distribution": risk_data,
        "breached_passwords": breached_count,
        "average_score": round(avg_score_val, 2),
        "score_ranges": score_ranges,
        "breached_percentage": round((breached_count / total_count * 100) if total_count > 0 else 0, 2),
    }


@router.get("/dashboard/recent-checks")
async def get_recent_checks(
    limit: int = Query(20, ge=1, le=100),
    current_user: dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> list[dict[str, Any]]:
    """Get recent password checks for audit log"""
    result = (
        await db.execute(
            text("""
                SELECT
                    id::text,
                    user_id::text,
                    score,
                    strength_label,
                    risk_label,
                    is_breached,
                    breach_count,
                    created_at
                FROM password_checks
                ORDER BY created_at DESC
                LIMIT :limit
            """),
            {"limit": limit},
        )
    ).fetchall()

    checks = []
    for row in result:
        checks.append({
            "id": row[0],
            "user_id": row[1],
            "score": row[2],
            "strength_label": row[3],
            "risk_label": row[4],
            "is_breached": row[5],
            "breach_count": row[6],
            "created_at": row[7].isoformat() if row[7] else None,
        })

    return checks


@router.get("/dashboard/strength-timeline")
async def get_strength_timeline(
    days: int = Query(7, ge=1, le=90),
    current_user: dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Get password strength trend over time"""
    result = (
        await db.execute(
            text("""
                SELECT
                    DATE(created_at) as date,
                    AVG(score) as avg_score,
                    COUNT(*) as check_count
                FROM password_checks
                WHERE created_at >= NOW() - INTERVAL '1 day' * :days
                GROUP BY DATE(created_at)
                ORDER BY date ASC
            """),
            {"days": days},
        )
    ).fetchall()

    timeline = []
    for row in result:
        timeline.append({
            "date": row[0].isoformat() if row[0] else None,
            "average_score": round(float(row[1]), 2) if row[1] else 0,
            "check_count": row[2],
        })

    return {"timeline": timeline, "days": days}
