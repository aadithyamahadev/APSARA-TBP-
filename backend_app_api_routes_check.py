from fastapi import APIRouter, Header, HTTPException, status

from app.models.schemas import CheckPasswordRequest, CheckPasswordResponse
from app.services.hibp import is_suffix_breached
from app.services.policy_engine import evaluate_policy
from app.services.tenant import resolve_tenant_from_api_key

router = APIRouter(prefix="/v1", tags=["check"])


@router.post("/check", response_model=CheckPasswordResponse)
async def check_password(
    payload: CheckPasswordRequest,
    x_api_key: str | None = Header(default=None),
) -> CheckPasswordResponse:
    try:
        tenant = resolve_tenant_from_api_key(x_api_key)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        ) from exc

    breached = False
    if tenant.policy.hibp_check:
        breached = await is_suffix_breached(payload.sha1_prefix, payload.sha1_suffix)

    return evaluate_policy(payload, tenant.policy, breached)
