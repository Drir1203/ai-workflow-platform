"""AI 写作 SSE 端点：POST /api/writing → text/event-stream。

协议：每行 ``data: {json}\n\n``。引擎未配置/首调失败也走 error+done 事件
（全请求 200），客户端契约明确。纯文本变换，无 DB 依赖。
"""

import json

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from ..ai import AiEngine, get_ai_engine
from ..ai.errors import AiEngineUnavailable
from ..api.deps import get_current_user
from ..config import settings
from ..core.ratelimit import rate_limit
from ..models.user import User
from . import service
from .schemas import WritingRequest

router = APIRouter(prefix="/api/writing", tags=["writing"])

# 限流：与 AI 对话/副驾共享同一 llm 桶（来源 IP 滑动窗口），控成本
_llm_limit = rate_limit(settings.ratelimit_llm_per_min, 60, scope="llm")


@router.post("")
async def writing(
    payload: WritingRequest,
    _rl: None = Depends(_llm_limit),
    engine: AiEngine = Depends(get_ai_engine),
    user: User = Depends(get_current_user),
) -> StreamingResponse:
    async def gen():
        try:
            async for ev in service.stream_writing(engine, user, payload.operation, payload.text):
                yield "data: {}\n\n".format(json.dumps(ev, ensure_ascii=False))
        except AiEngineUnavailable as exc:
            # 引擎未配置：走错误事件而非 503（流已开始，HTTP 状态码已定）
            yield "data: {}\n\n".format(
                json.dumps(service.event_error("ai_unavailable", str(exc)), ensure_ascii=False)
            )
            yield "data: {}\n\n".format(json.dumps(service.event_done(), ensure_ascii=False))
        except Exception:  # noqa: BLE001
            # 兜底：绝不让流式连接以异常终止（前端等 done 收尾）
            yield "data: {}\n\n".format(
                json.dumps(service.event_error("internal", "服务异常，请稍后重试"), ensure_ascii=False)
            )
            yield "data: {}\n\n".format(json.dumps(service.event_done(), ensure_ascii=False))

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        # X-Accel-Buffering=no：关 nginx 缓冲，让流式增量即时到达浏览器
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
