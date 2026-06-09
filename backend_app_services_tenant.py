from dataclasses import dataclass

from app.core.config import get_settings
from app.models.policy import TenantPolicy


@dataclass
class TenantContext:
    tenant_id: str
    policy: TenantPolicy


# Scaffold-only lookup. Replace with hashed API key lookup in Supabase.
_DEMO_KEYS: dict[str, str] = {
    get_settings().demo_tenant_api_key: "00000000-0000-0000-0000-000000000001"
}


def resolve_tenant_from_api_key(api_key: str | None) -> TenantContext:
    if not api_key or api_key not in _DEMO_KEYS:
        raise ValueError("Invalid API key")

    tenant_id = _DEMO_KEYS[api_key]
    return TenantContext(tenant_id=tenant_id, policy=TenantPolicy())
