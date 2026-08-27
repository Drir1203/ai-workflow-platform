"""AI 写作模块：续写 / 润色 / 总结。

独立于 copilot 的意图路由——这三者是确定性动作，直接调 AiEngine.stream_chat
流式输出，避免多一次 LLM 意图解析的开销与延迟。
"""
