import math
from typing import Any

from fastapi import APIRouter, Depends, Header
from zxcvbn import zxcvbn

from app.middleware.auth import get_current_user
from app.models.schemas import AnalyzePasswordRequest, AnalyzePasswordResponse
from app.services.policy_service import get_all_policies

router = APIRouter(prefix="/analyze", tags=["analyze"])


def _calculate_entropy_bits(password: str) -> float:
    has_lower = any(char.islower() for char in password)
    has_upper = any(char.isupper() for char in password)
    has_digit = any(char.isdigit() for char in password)
    has_special = any(not char.isalnum() for char in password)

    charset_size = 0
    if has_lower:
        charset_size += 26
    if has_upper:
        charset_size += 26
    if has_digit:
        charset_size += 10
    if has_special:
        charset_size += 32

    if charset_size == 0:
        return 0.0

    return float(len(password) * math.log2(charset_size))


def _extract_patterns(result: dict[str, Any]) -> list[str]:
    matches = result.get("sequence", [])
    found: set[str] = set()

    if isinstance(matches, list):
        for match in matches:
            if not isinstance(match, dict):
                continue
            pattern = match.get("pattern")
            if pattern == "spatial":
                found.add("keyboard patterns")
            elif pattern == "repeat":
                found.add("repeats")
            elif pattern == "dictionary":
                found.add("dictionary words")
            elif pattern == "date":
                found.add("dates")
            elif pattern == "sequence":
                found.add("sequences")

    ordered_patterns = [
        "keyboard patterns",
        "repeats",
        "dictionary words",
        "dates",
        "sequences",
    ]
    return [pattern for pattern in ordered_patterns if pattern in found]


def _extract_crack_time_display(result: dict[str, Any]) -> str:
    crack_times_display = result.get("crack_times_display")
    if isinstance(crack_times_display, dict):
        # Prefer realistic user-facing scenarios before the fastest offline attack.
        preferred_keys = [
            "offline_slow_hashing_1e4_per_second",
            "online_no_throttling_10_per_second",
            "online_throttling_100_per_hour",
            "offline_fast_hashing_1e10_per_second",
        ]

        for key in preferred_keys:
            value = crack_times_display.get(key)
            if isinstance(value, str) and value:
                return value

        for value in crack_times_display.values():
            if isinstance(value, str) and value:
                return value

    legacy = result.get("crack_time_display")
    if isinstance(legacy, str) and legacy:
        return legacy

    return "unknown"


def _score_to_label(score: int) -> str:
    label_map = {
        0: "very weak",
        1: "weak",
        2: "fair",
        3: "strong",
        4: "very strong",
    }
    return label_map.get(score, "very weak")


def _build_recommendations(
    feedback_suggestions: list[str],
    entropy_bits: float,
    has_special_chars: bool,
) -> list[str]:
    recommendations: list[str] = []

    for suggestion in feedback_suggestions:
        if isinstance(suggestion, str):
            cleaned = suggestion.strip()
            if cleaned:
                recommendations.append(cleaned)

    if entropy_bits < 40:
        recommendations.append("Use a longer password to increase entropy (target at least 40 bits).")

    if not has_special_chars:
        recommendations.append("Add special characters to increase complexity.")

    deduped: list[str] = []
    seen: set[str] = set()
    for recommendation in recommendations:
        if recommendation not in seen:
            deduped.append(recommendation)
            seen.add(recommendation)

    return deduped


def _build_requirement_recommendations(password: str, reqs: dict[str, Any]) -> tuple[list[str], list[str]]:
    recommendations: list[str] = []
    violations: list[str] = []
    password_length = len(password)

    min_length = reqs.get("min_length")
    max_length = reqs.get("max_length")

    if isinstance(min_length, int) and password_length < min_length:
        message = f"This service requires a minimum length of {min_length} characters"
        recommendations.append(message)
        violations.append("min_length")

    if isinstance(max_length, int) and password_length > max_length:
        message = f"This service requires a maximum length of {max_length} characters"
        recommendations.append(message)
        violations.append("max_length")

    if reqs.get("require_uppercase") is True and not any(char.isupper() for char in password):
        recommendations.append("This service requires at least one uppercase letter")
        violations.append("require_uppercase")

    if reqs.get("require_lowercase") is True and not any(char.islower() for char in password):
        recommendations.append("This service requires at least one lowercase letter")
        violations.append("require_lowercase")

    if reqs.get("require_digit") is True and not any(char.isdigit() for char in password):
        recommendations.append("This service requires at least one digit")
        violations.append("require_digit")

    if reqs.get("require_special") is True and all(char.isalnum() for char in password):
        recommendations.append("This service requires at least one special character")
        violations.append("require_special")

    return recommendations, violations


@router.post("", response_model=AnalyzePasswordResponse)
async def analyze_password(
    payload: AnalyzePasswordRequest,
    x_service_id: str | None = Header(default=None, alias="X-Service-ID"),
    _: dict[str, Any] = Depends(get_current_user),
) -> AnalyzePasswordResponse:
    password = payload.password
    service_id = (x_service_id or "default").strip() or "default"
    policies = await get_all_policies(service_id)
    reqs = policies.get("password_requirements", {})

    entropy_bits = _calculate_entropy_bits(password)
    has_special_chars = any(not char.isalnum() for char in password)

    result = zxcvbn(password)
    raw_score = result.get("score", 0)
    score = raw_score if isinstance(raw_score, int) else 0
    if score < 0 or score > 4:
        score = 0

    feedback = result.get("feedback", {})
    suggestions = feedback.get("suggestions", []) if isinstance(feedback, dict) else []
    feedback_suggestions = suggestions if isinstance(suggestions, list) else []

    recommendations = _build_recommendations(feedback_suggestions, entropy_bits, has_special_chars)
    requirement_recommendations, policy_violations = _build_requirement_recommendations(password, reqs)
    recommendations.extend(requirement_recommendations)

    deduped_recommendations: list[str] = []
    seen: set[str] = set()
    for recommendation in recommendations:
        if recommendation not in seen:
            deduped_recommendations.append(recommendation)
            seen.add(recommendation)

    return AnalyzePasswordResponse(
        entropy_bits=entropy_bits,
        zxcvbn_score=score,
        strength_label=_score_to_label(score),
        crack_time_display=_extract_crack_time_display(result),
        patterns_detected=_extract_patterns(result),
        recommendations=deduped_recommendations,
        policy_violations=policy_violations,
    )