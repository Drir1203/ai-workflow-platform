"""AI 对话副驾（Copilot）：全局对话入口 → 意图路由 → 调度 Agent / 工作流 / 知识库 / 创建任务项目。

模块分层：
- schemas.py  请求/消息 Pydantic 模型
- prompts.py  意图路由系统提示词构造（把当前租户能力清单注入 LLM）
- service.py  意图解析 + 分发 + SSE 事件流（核心）
- router.py   POST /api/copilot/chat → StreamingResponse
"""
