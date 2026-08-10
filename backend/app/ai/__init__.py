from .base import AiEngine
from .dify import DifyEngine


def get_ai_engine() -> AiEngine:
    """DI 工厂：返回配置好的 AI 引擎（当前为 Dify CE headless）。"""
    return DifyEngine()
