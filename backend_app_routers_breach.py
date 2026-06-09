import hashlib
from typing import Any

import httpx
from fastapi import APIRouter, Depends

from app.core.config import get_settings
from app.middleware.auth import get_current_user
from app.models.schemas import BreachCheckRequest, BreachCheckResponse
from app.redis_client import redis_client
from app.services.policy_service import get_default_policy_value, get_policy

router = APIRouter(prefix="/check-breach", tags=["breach"])

_HIBP_RETRY_ATTEMPTS = 2
_HIBP_UNAVAILABLE_ERROR = "breach check unavailable"


def _extract_breach_count(range_payload: str, suffix: str) -> int:
    normalized_suffix = suffix.upper()

    for line in range_payload.splitlines():
        if not line:
            continue
        parts = line.split(":", 1)
        if len(parts) != 2:
            continue

        candidate_suffix, candidate_count = parts
        if candidate_suffix.strip().upper() != normalized_suffix:
            continue

        try:
            return int(candidate_count.strip())
        except ValueError:
            return 0

    return 0


async def _fetch_hibp_range_payload(prefix: str) -> str:
    settings = get_settings()
    url = f"{settings.hibp_base_url}/{prefix}"
    headers = {
        "Add-Padding": "true",
        "User-Agent": "Apsara-PasswordChecker",
    }

    last_error: Exception | None = None
    for _ in range(_HIBP_RETRY_ATTEMPTS):
        try:
            async with httpx.AsyncClient(timeout=settings.hibp_timeout_seconds) as client:
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                return response.text
        except (httpx.TimeoutException, httpx.HTTPError) as exc:
            last_error = exc

    if last_error is not None:
        raise last_error

    raise RuntimeError("Unexpected HIBP fetch state")


@router.post("", response_model=BreachCheckResponse)
async def check_breach(
    payload: BreachCheckRequest,
    _: dict[str, Any] = Depends(get_current_user),
) -> BreachCheckResponse:
    ttl_policy = await get_policy("default", "breach_cache_ttl")
    ttl_seconds = ttl_policy.get("seconds")
    if not isinstance(ttl_seconds, int) or ttl_seconds <= 0:
        ttl_seconds = int(get_default_policy_value("breach_cache_ttl")["seconds"])

    full_hash = hashlib.sha1(payload.password.encode()).hexdigest().upper()
    prefix = full_hash[:5]
    suffix = full_hash[5:]

    cache_key = f"hibp:{prefix}"
    cached_payload = await redis_client.get(cache_key)

    cache_hit = False
    hibp_range_payload: str | None = None

    if isinstance(cached_payload, str) and cached_payload:
        hibp_range_payload = cached_payload
        cache_hit = True
    else:
        try:
            hibp_range_payload = await _fetch_hibp_range_payload(prefix)
            await redis_client.set(
                cache_key,
                hibp_range_payload,
                expire_seconds=ttl_seconds,
            )
        except (httpx.TimeoutException, httpx.HTTPError):
            return BreachCheckResponse(
                is_breached=None,
                breach_count=0,
                cache_hit=False,
                error=_HIBP_UNAVAILABLE_ERROR,
            )

    breach_count = _extract_breach_count(hibp_range_payload or "", suffix)
    return BreachCheckResponse(
        is_breached=breach_count > 0,
        breach_count=breach_count,
        cache_hit=cache_hit,
        error=None,
    )
