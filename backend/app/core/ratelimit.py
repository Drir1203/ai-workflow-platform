"""进程内滑动窗口限流器（单 worker 部署，与 APScheduler 同假设）。

按「来源 IP + scope」维度做滑动窗口计数，超限抛 429。
sync 的 hit() 内无 await，在单线程事件循环里天然原子，无竞态。
测试通过 monkeypatch `settings.ratelimit_enabled` 或 `reset_limiter()` 隔离。
"""

from __future__ import annotations

import time
from collections import defaultdict, deque
from typing import Callable

from fastapi import HTTPException, Request, status

from ..config import settings


class RateLimitExceeded(Exception):
    """窗口内请求数超限。"""


class MemoryRateLimiter:
    """滑动窗口计数：只保留窗口期内的命中间隔，超限拒绝。"""

    def __init__(self) -> None:
        self._buckets: dict[str, deque[float]] = defaultdict(deque)

    def reset(self) -> None:
        self._buckets.clear()

    def hit(self, key: str, limit: int, window_seconds: float) -> None:
        now = time.monotonic()
        bucket = self._buckets[key]
        while bucket and bucket[0] <= now - window_seconds:
            bucket.popleft()
        if len(bucket) >= limit:
            raise RateLimitExceeded
        bucket.append(now)


_limiter = MemoryRateLimiter()


def reset_limiter() -> None:
    """清空计数（测试隔离用）。"""
    _limiter.reset()


def rate_limit(limit: int, window_seconds: float = 60.0, *, scope: str = "global") -> Callable:
    """FastAPI 依赖工厂：`Depends(rate_limit(n, 60, scope="auth"))`。

    limit 与窗口配置来自 settings（如 `settings.ratelimit_auth_per_min`），
    读的是当前值而非工厂调用时的快照，便于测试内 monkeypatch。
    """

    async def dependency(request: Request) -> None:
        if not settings.ratelimit_enabled:
            return
        ip = request.client.host if request.client else "unknown"
        try:
            _limiter.hit(f"{scope}:{ip}", limit, window_seconds)
        except RateLimitExceeded:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="请求过于频繁，请稍后再试",
            )

    return dependency
