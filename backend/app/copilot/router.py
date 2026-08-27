"""AI 副驾 SSE 端点：POST /api/copilot/chat → text/event-stream。

协议：每行 ``data: {json}\\n\\n``（JSON 事件见 service 模块注释）。
引擎未配置/首调失败也走 error+done 事件（全请求 200），客户端契约明确。
"""

import json

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from ..ai import AiEngine, get_ai_engine
from ..ai.errors import AiEngineUnavailable
from ..config import settings
from ..core.ratelimit import rate_limit
from ..db import get_db
from ..models.user import User
from . import service
from .schemas import CopilotChatRequest
from ..api.deps import get_current_user

router = APIRouter(prefix="/api/copilot", tags=["copilot"])

# 限流：与 /api/ai/chat 同桶（来源 IP + llm 滑动窗口），控成本
_llm_limit = rate_limit(settings.ratelimit_llm_per_min, 60, scope="llm")


@router.post("/chat")
async def copilot_chat(
    payload: CopilotChatRequest,
    _rl: None = Depends(_llm_limit),
    db: AsyncSession = Depends(get_db),
    engine: AiEngine = Depends(get_ai_engine),
    user: User = Depends(get_current_user),
) -> StreamingResponse:
    messages = [m.model_dump() for m in payload.messages]

    async def gen():
        try:
            async for ev in service.stream_response(
                db, user, engine, messages, payload.project_id
            ):
                yield "data: {}\n\n".format(json.dumps(ev, ensure_ascii=False))
        except AiEngineUnavailable as exc:
            # 引擎未配置：走错误事件而非 503（流已开始，HTTP 状态码已定）
            yield "data: {}\n\n".format(
                json.dumps(service.event_error("ai_unavailable", str(exc)), ensure_ascii=False)
            )
            yield "data: {}\n\n".format(json.dumps(service.event_done(), ensure_ascii=False))
        except Exception as exc:  # noqa: BLE001
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
