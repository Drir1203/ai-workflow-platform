from ..config import settings
from .base import AiEngine
from .dify import DifyEngine
from .openai_compatible import OpenAICompatibleEngine


def get_ai_engine() -> AiEngine:
    """DI 工厂：按配置选择 AI 引擎。dify=Dify CE headless；openai_compatible=DeepSeek/通义等。"""
    if settings.ai_provider == "openai_compatible":
        return OpenAICompatibleEngine()
    return DifyEngine()
