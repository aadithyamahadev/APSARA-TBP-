import httpx

from app.core.config import get_settings


async def is_suffix_breached(prefix: str, suffix: str) -> bool:
    """Query HIBP range API using k-anonymity and check suffix in-memory."""
    settings = get_settings()
    url = f"{settings.hibp_base_url}/{prefix.upper()}"

    async with httpx.AsyncClient(timeout=settings.hibp_timeout_seconds) as client:
        response = await client.get(url)
        response.raise_for_status()

    normalized_suffix = suffix.upper()
    for line in response.text.splitlines():
        candidate, _count = line.split(":")
        if candidate.upper() == normalized_suffix:
            return True

    return False
