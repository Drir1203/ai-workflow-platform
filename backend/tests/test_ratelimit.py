"""限流测试：进程内滑动窗口按 IP+scope 计数，超限返回 429。

conftest 默认关闭限流（ratelimit_enabled=False），本文件用 autouse fixture
单独打开并 reset_limiter() 隔离。窗口额度读 settings 当前值（依赖闭包在
import 时快照），故「超限」用默认额度 + 1 次请求触发，而非 monkeypatch 额度。
"""

import pytest

from app.config import settings
from app.core.ratelimit import reset_limiter

_REGISTER = {
    "password": "secret123",
    "name": "限流",
}


@pytest.fixture(autouse=True)
def _enable_ratelimit(monkeypatch):
    # 本文件单独打开限流（conftest 默认关），且每用例前后清空窗口计数，避免用例间串扰
    monkeypatch.setattr(settings, "ratelimit_enabled", True)
    reset_limiter()
    yield
    reset_limiter()


async def _register(client, email: str, expect: set[int]) -> None:
    r = await client.post("/api/auth/register", json={**_REGISTER, "email": email})
    assert r.status_code in expect, f"POST register {email} → {r.status_code}，期望 {expect}"


async def test_auth_limit_rejects_overflow(client):
    """登录/注册防爆破：超过 auth 窗口额度后第 N+1 次请求返回 429。

    首次注册 201、邮箱重复 409 都计入窗口（限流先于端点逻辑执行），
    证明失败尝试同样消耗预算、不能靠重复邮箱绕过。
    """
    limit = settings.ratelimit_auth_per_min
    for i in range(limit):
        await _register(client, f"rl-{i}@test.com", {201, 409})
    r = await client.post(
        "/api/auth/register", json={**_REGISTER, "email": "rl-over@test.com"}
    )
    assert r.status_code == 429


async def test_reset_limiter_clears_window(client):
    """reset_limiter() 清空窗口后，同一 IP 可继续请求。"""
    limit = settings.ratelimit_auth_per_min
    for i in range(limit):
        await _register(client, f"rl-b-{i}@test.com", {201, 409})
    await _register(client, "rl-b-over@test.com", {429})

    reset_limiter()
    await _register(client, "rl-b-ok@test.com", {201, 409})


async def test_ratelimit_disabled_is_noop(client, monkeypatch):
    """关闭限流后，同 IP 高频请求不返回 429。"""
    monkeypatch.setattr(settings, "ratelimit_enabled", False)
    reset_limiter()
    for i in range(settings.ratelimit_auth_per_min + 5):
        await _register(client, f"rl-off-{i}@test.com", {201, 409})


async def test_scopes_are_isolated(client):
    """不同 scope 计数独立：auth 打满不影响 llm scope。

    /api/ai/chat 无凭证应 401（认证依赖）而非 429（auth 限流），
    证明 auth 窗口的溢出没有波及 llm 窗口。
    """
    limit = settings.ratelimit_auth_per_min
    for i in range(limit):
        await _register(client, f"rl-c-{i}@test.com", {201, 409})
    r = await client.post("/api/ai/chat", json={"query": "hi"})
    assert r.status_code == 401
