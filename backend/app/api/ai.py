from fastapi import APIRouter, Depends, HTTPException, status

from ..ai import AiEngine, get_ai_engine
from ..ai.errors import AiEngineUnavailable
from ..models.user import User
from ..schemas.ai import ChatRequest, ChatResponse
from .deps import get_current_user

router = APIRouter(prefix="/api/ai", tags=["ai"])


@router.post("/chat", response_model=ChatResponse)
async def chat(
    payload: ChatRequest,
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
    engine: AiEngine = Depends(get_ai_engine),
    user: User = Depends(get_current_user),
) -> ChatResponse:
    try:
        answer = await engine.knowledge_query(payload.query, user.id)
    except AiEngineUnavailable as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))
    return ChatResponse(answer=answer)
