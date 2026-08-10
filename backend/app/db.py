from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from .config import settings

# PostgreSQL 走连接池 + 断线重连；SQLite（本地/测试）不适用这些参数。
engine_kwargs: dict = {}
if settings.database_url.startswith("postgresql"):
    engine_kwargs = {"pool_size": 5, "max_overflow": 10, "pool_pre_ping": True}

engine = create_async_engine(settings.database_url, echo=False, **engine_kwargs)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session
