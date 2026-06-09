from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = Field(default="APSARA API", alias="APP_NAME")
    env: str = Field(default="development", alias="ENV")
    version: str = Field(default="0.1.0", alias="VERSION")
    
    frontend_url: str = Field(default="http://localhost:3000", alias="FRONTEND_URL")
    cors_allow_origins: str = Field(default="http://localhost:3000", alias="CORS_ALLOW_ORIGINS")
    
    hibp_base_url: str = Field(default="https://api.pwnedpasswords.com/range", alias="HIBP_BASE_URL")
    hibp_timeout_seconds: int = Field(default=5, alias="HIBP_TIMEOUT_SECONDS")

    demo_tenant_api_key: str = Field(default="sk_demo_local_please_rotate", alias="DEMO_TENANT_API_KEY")

    database_url: str = Field(alias="DATABASE_URL")
    upstash_redis_rest_url: str = Field(alias="UPSTASH_REDIS_REST_URL")
    upstash_redis_rest_token: str = Field(alias="UPSTASH_REDIS_REST_TOKEN")
    jwt_secret: str = Field(alias="JWT_SECRET")
    jwt_expire_minutes: int = Field(default=60, alias="JWT_EXPIRE_MINUTES")

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_allow_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
