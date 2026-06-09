import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import bindparam, text
from sqlalchemy.dialects.postgresql import JSONB

from app.api.router import api_router
from app.core.config import get_settings
from app.db import AsyncSessionLocal
from app.routers.admin import router as admin_router
from app.routers.analyze import router as analyze_router
from app.routers.auth import router as auth_router
from app.routers.breach import router as breach_router
from app.routers.score import router as score_router
from app.services.audit import get_request_ip, safe_write_audit_log

settings = get_settings()
logger = logging.getLogger(__name__)


DEFAULT_POLICY_CONFIGS = [
	{"name": "max_password_length", "value": 128},
	{"name": "rate_limit_per_min", "value": 30},
	{"name": "breach_cache_ttl_seconds", "value": 86400},
]

app = FastAPI(title=settings.app_name)
app.add_middleware(
	CORSMiddleware,
	allow_origins=settings.cors_origins_list,
	allow_credentials=False,
	allow_methods=["*"],
	allow_headers=["*"],
)

app.include_router(api_router)
app.include_router(auth_router)
app.include_router(analyze_router)
app.include_router(breach_router)
app.include_router(score_router)
app.include_router(admin_router)


@app.on_event("startup")
async def seed_policy_configs() -> None:
	try:
		async with AsyncSessionLocal() as db:
			for policy in DEFAULT_POLICY_CONFIGS:
				await db.execute(
					text(
						"""
						INSERT INTO policy_configs (service_id, name, value, description, updated_at)
						VALUES (:service_id, :name, :value, :description, now())
						ON CONFLICT (service_id, name) DO NOTHING
						"""
					).bindparams(bindparam("value", type_=JSONB)),
					{
						"service_id": "default",
						"name": policy["name"],
						"value": policy["value"],
						"description": "Seeded baseline configuration",
					},
				)
			await db.commit()
	except Exception:
		logger.exception("policy seed startup task failed")


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
	await safe_write_audit_log(
		action="server_error",
		ip_address=get_request_ip(request),
		metadata={
			"method": request.method,
			"path": request.url.path,
			"error_type": exc.__class__.__name__,
		},
	)
	return JSONResponse(status_code=500, content={"detail": "internal server error"})
