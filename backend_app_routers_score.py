from __future__ import annotations

import hashlib
from typing import Any

import httpx
from fastapi import APIRouter, Depends, Header, Request
from sqlalchemy import bindparam, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession
from zxcvbn import zxcvbn  # type: ignore

from app.dependencies import get_db_session
from app.middleware.auth import get_current_user
from app.models.schemas import ScorePasswordRequest, ScorePasswordResponse
from app.redis_client import redis_client
from app.routers.analyze import (
    _build_recommendations,
    _build_requirement_recommendations,
    _calculate_entropy_bits,
    _extract_crack_time_display,
    _extract_patterns,
    _score_to_label,
)
from app.routers.breach import (
    _extract_breach_count,
    _fetch_hibp_range_payload,
)
from app.services.audit import get_request_ip, safe_write_audit_log
from app.services.policy_service import get_all_policies, get_default_policy_value

router = APIRouter(prefix="/score", tags=["score"])


def _clamp_score(value: int, min_score: int, max_score: int) -> int:
    return max(min_score, min(max_score, value))


def _to_int(value: Any, default: int) -> int:
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    return default


def _merged_policy(policy: dict[str, Any], name: str) -> dict[str, Any]:
    merged = get_default_policy_value(name)
    candidate = policy.get(name)
    if isinstance(candidate, dict):
        merged.update(candidate)
    return merged


def _risk_label_from_thresholds(score: int, thresholds: dict[str, Any]) -> str:
    for label, current in thresholds.items():
        if isinstance(current, list) and len(current) == 2 and all(isinstance(item, int) for item in current):
            if current[0] <= score <= current[1]:
                return label

    if thresholds:
        return str(next(iter(thresholds.keys())))
    return "unknown"


def _score_bounds_from_thresholds(thresholds: dict[str, Any]) -> tuple[int, int]:
    ranges: list[tuple[int, int]] = []
    for current in thresholds.values():
        if isinstance(current, list) and len(current) == 2 and all(isinstance(item, int) for item in current):
            ranges.append((current[0], current[1]))

    if not ranges:
        return (0, 0)

    min_score = min(current[0] for current in ranges)
    max_score = max(current[1] for current in ranges)
    return (min_score, max_score)


def _pattern_penalty_total(patterns_detected: list[str], pattern_policy: dict[str, Any]) -> int:
    label_to_policy = {
        "keyboard patterns": "keyboard",
        "repeats": "repeat",
        "dictionary words": "dictionary",
        "dates": "date",
        "sequences": "sequence",
    }

    total = 0
    for detected in patterns_detected:
        policy_key = label_to_policy.get(detected)
        if policy_key is None:
            continue
        total += _to_int(pattern_policy.get(policy_key), 0)

    return total


@router.post("", response_model=ScorePasswordResponse)
async def score_password(
    payload: ScorePasswordRequest,
    request: Request,
    x_service_id: str | None = Header(default=None, alias="X-Service-ID"),
    current_user: dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> ScorePasswordResponse:
    password = payload.password
    service_id = (x_service_id or "default").strip() or "default"
    policy = await get_all_policies(service_id)

    score_weights = _merged_policy(policy, "score_weights")
    entropy_bonus_policy = _merged_policy(policy, "entropy_bonus")
    breach_penalty_policy = _merged_policy(policy, "breach_penalty")
    pattern_penalty_policy = _merged_policy(policy, "pattern_penalty")
    risk_thresholds_policy = _merged_policy(policy, "risk_thresholds")
    breach_cache_ttl_policy = _merged_policy(policy, "breach_cache_ttl")
    password_requirements_policy = _merged_policy(policy, "password_requirements")

    # Check for top-level max_password_length policy override from DB
    try:
        max_length_row = (
            (
                await db.execute(
                    text(
                        """
                        SELECT value
                        FROM policy_configs
                        WHERE service_id = :service_id AND name = 'max_password_length'
                        LIMIT 1
                        """
                    ),
                    {"service_id": service_id},
                )
            )
            .mappings()
            .first()
        )
        if max_length_row is not None and max_length_row["value"] is not None:
            db_max_length = max_length_row["value"]
            if isinstance(db_max_length, int):
                password_requirements_policy["max_length"] = db_max_length
    except Exception:
        pass

    min_risk_score, max_risk_score = _score_bounds_from_thresholds(risk_thresholds_policy)

    entropy_bits = _calculate_entropy_bits(password)
    has_special_chars = any(not char.isalnum() for char in password)

    zxcvbn_result = zxcvbn(password)
    result_dict = dict(zxcvbn_result)

    raw_score = result_dict.get("score")
    zxcvbn_score = raw_score if isinstance(raw_score, int) else None
    if zxcvbn_score is None or str(zxcvbn_score) not in score_weights:
        zxcvbn_score = int(next(iter(score_weights.keys())))

    feedback = result_dict.get("feedback", {})
    suggestions = feedback.get("suggestions", []) if isinstance(feedback, dict) else []
    feedback_suggestions = suggestions if isinstance(suggestions, list) else []

    patterns_detected = _extract_patterns(result_dict)

    full_hash = hashlib.sha1(password.encode()).hexdigest().upper()
    prefix = full_hash[:5]
    suffix = full_hash[5:]

    cache_key = f"hibp:{prefix}"
    cached_payload = await redis_client.get(cache_key)

    cache_hit = False
    hibp_range_payload: str | None = None
    cache_ttl_seconds = _to_int(breach_cache_ttl_policy.get("seconds"), 1)

    if isinstance(cached_payload, str) and cached_payload:
        hibp_range_payload = cached_payload
        cache_hit = True
    else:
        try:
            hibp_range_payload = await _fetch_hibp_range_payload(prefix)
            await redis_client.set(
                cache_key,
                hibp_range_payload,
                expire_seconds=cache_ttl_seconds,
            )
        except (httpx.TimeoutException, httpx.HTTPError):
            hibp_range_payload = None

    breach_count = _extract_breach_count(hibp_range_payload or "", suffix)
    is_breached: bool | None
    if hibp_range_payload is None:
        is_breached = None
        breach_count = 0
        cache_hit = False
    else:
        is_breached = breach_count > 0

    score = _to_int(score_weights.get(str(zxcvbn_score)), min_risk_score)

    entropy_threshold_bits = _to_int(entropy_bonus_policy.get("threshold_bits"), min_risk_score)
    entropy_bonus_points = _to_int(entropy_bonus_policy.get("bonus_points"), min_risk_score)
    if entropy_bits > entropy_threshold_bits:
        score += entropy_bonus_points

    if is_breached is True:
        score -= _to_int(breach_penalty_policy.get("points"), min_risk_score)

    score -= _pattern_penalty_total(patterns_detected, pattern_penalty_policy)

    score = _clamp_score(score, min_risk_score, max_risk_score)
    risk_label = _risk_label_from_thresholds(score, risk_thresholds_policy)

    recommendations = _build_recommendations(
        feedback_suggestions,
        entropy_bits,
        has_special_chars,
    )
    requirement_recommendations, policy_violations = _build_requirement_recommendations(
        password,
        password_requirements_policy,
    )
    recommendations.extend(requirement_recommendations)

    if is_breached is True:
        recommendations.append(
            "This password appears in known data breaches. Use a new password not used elsewhere."
        )
    elif is_breached is None:
        recommendations.append(
            "Breach status could not be verified right now. Recheck before using this password."
        )

    deduped_recommendations: list[str] = []
    seen: set[str] = set()
    for item in recommendations:
        if item not in seen:
            deduped_recommendations.append(item)
            seen.add(item)

    ip_address = get_request_ip(request)
    audit_metadata = {
        "service_id": service_id,
        "score": score,
        "risk_label": risk_label,
        "is_breached": is_breached,
        "breach_count": breach_count,
        "entropy_bits": entropy_bits,
        "policy_violations": policy_violations,
    }

    await safe_write_audit_log(
        action="password_scored",
        user_id=current_user["id"],
        ip_address=ip_address,
        metadata=audit_metadata,
    )

    # Log to password_checks table for admin analytics
    try:
        await db.execute(
            text("""
                INSERT INTO password_checks 
                (user_id, score, strength_label, risk_label, is_breached, breach_count, entropy_bits, patterns_detected, crack_time_seconds, created_at)
                VALUES (:user_id, :score, :strength_label, :risk_label, :is_breached, :breach_count, :entropy_bits, :patterns_detected, :crack_time_seconds, now())
            """).bindparams(bindparam("patterns_detected", type_=JSONB)),
            {
                "user_id": current_user["id"],
                "score": score,
                "strength_label": _score_to_label(zxcvbn_score),
                "risk_label": risk_label,
                "is_breached": is_breached,
                "breach_count": breach_count,
                "entropy_bits": entropy_bits,
                "patterns_detected": patterns_detected,
                "crack_time_seconds": None,
            },
        )
    except Exception:
        pass  # Don't fail if analytics logging fails

    try:
        await db.commit()
    except Exception:
        pass

    return ScorePasswordResponse(
        service_id=service_id,
        score=score,
        risk_label=risk_label,
        strength_label=_score_to_label(zxcvbn_score),
        entropy_bits=entropy_bits,
        zxcvbn_score=zxcvbn_score,
        crack_time_display=_extract_crack_time_display(result_dict),
        is_breached=is_breached,
        breach_count=breach_count,
        patterns_detected=patterns_detected,
        recommendations=deduped_recommendations,
        policy_violations=policy_violations,
        cache_hit=cache_hit,
    )
