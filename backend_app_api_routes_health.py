from fastapi import APIRouter

from app.core.config import get_settings

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/")
async def health() -> dict[str, str]:
    settings = get_settings()
    return {
        "status": "ok",
        "version": settings.version,
        "env": settings.env,
    }
