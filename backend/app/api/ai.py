from fastapi import APIRouter, Depends, HTTPException, status

from ..ai import AiEngine, get_ai_engine
from ..ai.errors import AiEngineUnavailable
from ..config import settings
from ..core.ratelimit import rate_limit
from ..models.user import User
from ..schemas.ai import ChatRequest, ChatResponse
from .deps import get_current_user

router = APIRouter(prefix="/api/ai", tags=["ai"])

# 限流依赖：按「来源 IP + llm」滑动窗口计数，超限抛 429（AI 对话控成本）。
# 端点的 `_rl: None = Depends(...)` 参数不传值，只负责把该依赖挂进请求链路，见 core/ratelimit.py
_llm_limit = rate_limit(settings.ratelimit_llm_per_min, 60, scope="llm")


@router.post("/chat", response_model=ChatResponse)
async def chat(
    payload: ChatRequest,
    _rl: None = Depends(_llm_limit),
    engine: AiEngine = Depends(get_ai_engine),
    user: User = Depends(get_current_user),
) -> ChatResponse:
    try:
        answer = await engine.chat(payload.query, user.id)
    except AiEngineUnavailable as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))
    return ChatResponse(answer=answer)


@router.post("/knowledge", response_model=ChatResponse)
async def knowledge(
    payload: ChatRequest,
    _rl: None = Depends(_llm_limit),
    engine: AiEngine = Depends(get_ai_engine),
    user: User = Depends(get_current_user),
) -> ChatResponse:
    try:
        answer = await engine.knowledge_query(payload.query, user.id)
    except AiEngineUnavailable as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))
    return ChatResponse(answer=answer)
