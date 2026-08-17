import os

# 可选：指向真实 PostgreSQL（含迁移验证）——设置 TEST_DATABASE_URL 后，
# DATABASE_URL 一并指向它，使 app.config.settings 与 alembic env.py 都连到该库。
# 默认不设置则完全走内存 SQLite，无需任何外部服务。
TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")
if TEST_DATABASE_URL:
    os.environ["DATABASE_URL"] = TEST_DATABASE_URL

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.agents.runner import agent_run_manager
from app.db import SessionLocal, get_db
from app.workflows.executor import workflow_run_manager
from app.workflows.scheduler import workflow_scheduler
from app.config import settings
from app.main import app
from app.models import Base

# 测试套件默认关闭限流，避免并发/回归用例被 429 干扰。
# tests/test_ratelimit.py 内用 monkeypatch 单独打开并 reset_limiter() 隔离。
settings.ratelimit_enabled = False


@pytest.fixture(scope="session", autouse=True)
def _apply_migrations():
    """PG 路径下先跑一次 alembic upgrade head（迁移由 sync 上下文执行，env.py 内部 asyncio.run 可用）。"""
    if not TEST_DATABASE_URL:
        return
    from alembic import command
    from alembic.config import Config

    command.upgrade(Config("alembic.ini"), "head")


@pytest_asyncio.fixture
async def client():
    if TEST_DATABASE_URL:
        engine = create_async_engine(TEST_DATABASE_URL)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        # 迁移已建表；逐测试清空以隔离（子表先删，避免外键顺序问题）
        async with engine.begin() as conn:
            for table in reversed(Base.metadata.sorted_tables):
                await conn.execute(table.delete())
    else:
        # 临时文件 SQLite：后台任务与请求会话各用独立连接，靠 SQLite 文件锁串行化
        # （:memory: 单连接并发会破坏事务；共享缓存模式有 "statements in progress" 缺陷）
        import tempfile

        tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tmp.close()
        db_url = f"sqlite+aiosqlite:///{tmp.name}"
        engine = create_async_engine(db_url)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def override_get_db():
        async with factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    # 后台 Agent/Workflow 任务自开会话，指向测试库
    original_session_factory = agent_run_manager.session_factory
    agent_run_manager.session_factory = factory
    workflow_run_manager.session_factory = factory
    workflow_scheduler.session_factory = factory

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c

    await agent_run_manager.shutdown()
    await workflow_run_manager.shutdown()
    agent_run_manager.session_factory = original_session_factory
    workflow_run_manager.session_factory = SessionLocal
    workflow_scheduler.session_factory = SessionLocal
    app.dependency_overrides.clear()
    await engine.dispose()
    if not TEST_DATABASE_URL:
        os.unlink(tmp.name)


@pytest_asyncio.fixture
async def auth_headers(client):
    r = await client.post(
        "/api/auth/register",
        json={"email": "test@example.com", "password": "secret123", "name": "林"},
    )
    assert r.status_code == 201
    return {"Authorization": f"Bearer {r.json()['access_token']}"}
