"""
FastAPI dependencies for injecting database sessions and other runtime dependencies.
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from app.db import AsyncSessionLocal


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide an async SQLAlchemy session for a request lifetime.
    
    Usage in route:
        @router.get("/")
        async def my_route(db: AsyncSession = Depends(get_db_session)):
            ...
    """
    async with AsyncSessionLocal() as session:
        yield session
