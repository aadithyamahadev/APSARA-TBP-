from collections.abc import AsyncGenerator
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool

from app.core.config import get_settings


class Base(DeclarativeBase):
    pass


def _to_async_database_url(database_url: str) -> str:
    if database_url.startswith("postgresql+asyncpg://"):
        async_url = database_url
    elif database_url.startswith("postgresql://"):
        async_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    elif database_url.startswith("postgres://"):
        async_url = database_url.replace("postgres://", "postgresql+asyncpg://", 1)
    else:
        async_url = database_url

    # asyncpg expects 'ssl' query param, while many DSNs use libpq-style 'sslmode'.
    parsed = urlparse(async_url)
    query_items = parse_qsl(parsed.query, keep_blank_values=True)
    normalized_query: list[tuple[str, str]] = []
    has_ssl = False

    for key, value in query_items:
        if key == "ssl":
            has_ssl = True
            normalized_query.append((key, value))
            continue
        if key == "sslmode":
            if not has_ssl:
                normalized_query.append(("ssl", value))
                has_ssl = True
            continue
        normalized_query.append((key, value))

    return urlunparse(parsed._replace(query=urlencode(normalized_query)))


settings = get_settings()
engine = create_async_engine(
    _to_async_database_url(settings.database_url),
    pool_pre_ping=True,
    poolclass=NullPool,
    connect_args={
        "statement_cache_size": 0,
        "prepared_statement_cache_size": 0,
        "prepared_statement_name_func": lambda: f"__asyncpg_{uuid4()}__",
    },
)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session