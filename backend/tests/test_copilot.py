import pytest
from sqlalchemy import func, select

from app.ai import get_ai_engine
from app.ai.errors import AiEngineUnavailable
from app.main import app
from app.models.agent_run import AgentRun
from app.models.task import Task


class _CopilotEngine:
    """计数式假引擎：第 1 次 chat 返回意图 JSON，之后返回 agent 输出；stream_chat 整段产出。"""

    def __init__(self, intent="", outputs=("",), fail_with=None):
        self.intent = intent
        self.outputs = list(outputs)
        self.fail_with = fail_with  # AiEngineUnavailable 实例：首次 chat 即抛
        self.chat_count = 0
        self.stream_count = 0

    async def chat(self, query: str, user: str = "unknown") -> str:
        self.chat_count += 1
        if self.fail_with is not None:
            raise self.fail_with
        if self.chat_count == 1:
            return self.intent
        return self.outputs[min(self.chat_count - 2, len(self.outputs) - 1)]

    async def stream_chat(self, messages: list[dict], user: str = "unknown"):
        self.stream_count += 1
        if self.fail_with is not None:
            raise self.fail_with
        yield self.outputs[min(self.stream_count - 1, len(self.outputs) - 1)]


def _use_engine(engine: _CopilotEngine) -> None:
    app.dependency_overrides[get_ai_engine] = lambda: engine


def _drop_engine() -> None:
    app.dependency_overrides.pop(get_ai_engine, None)


async def test_copilot_requires_auth(client):
    r = await client.post(
        "/api/copilot/chat", json={"messages": [{"role": "user", "content": "hi"}]}
    )
    assert r.status_code == 401


async def test_copilot_answer_streams_text_and_done(client, auth_headers):
    engine = _CopilotEngine(intent='{"action":"answer"}', outputs=["你好副驾"])
    _use_engine(engine)
    try:
        r = await client.post(
            "/api/copilot/chat",
            json={"messages": [{"role": "user", "content": "你好"}]},
            headers=auth_headers,
        )
        assert r.status_code == 200
        assert '"type": "text"' in r.text
        assert "你好副驾" in r.text
        assert '"type": "done"' in r.text
    finally:
        _drop_engine()


async def test_copilot_intent_parse_failure_falls_back_to_answer(client, auth_headers):
    # 引擎返回非 JSON 垃圾 → 意图解析失败 → 回退 answer 流式回答
    engine = _CopilotEngine(intent="抱歉，我不是很理解", outputs=["兜底回答"])
    _use_engine(engine)
    try:
        r = await client.post(
            "/api/copilot/chat",
            json={"messages": [{"role": "user", "content": "随便聊聊"}]},
            headers=auth_headers,
        )
        assert r.status_code == 200
        assert "兜底回答" in r.text
        assert '"type": "done"' in r.text
    finally:
        _drop_engine()


async def test_copilot_run_agent_streams_result_and_persists(client, auth_headers, db_session):
    engine = _CopilotEngine(
        intent='{"action":"run_agent","params":{"agent_key":"weekly_report","params":{"period":"this_week"}}}',
        outputs=["周报内容：本周进展顺利"],
    )
    _use_engine(engine)
    try:
        r = await client.post(
            "/api/copilot/chat",
            json={"messages": [{"role": "user", "content": "帮我写本周周报"}]},
            headers=auth_headers,
        )
        assert r.status_code == 200
        assert '"type": "status"' in r.text
        assert '"kind": "agent"' in r.text
        assert "周报内容：本周进展顺利" in r.text
        assert '"type": "done"' in r.text
        # DB 断言：运行记录已落库且 succeeded
        rows = (await db_session.execute(select(AgentRun))).scalars().all()
        assert len(rows) == 1
        assert rows[0].status == "succeeded"
        assert rows[0].output == "周报内容：本周进展顺利"
    finally:
        _drop_engine()


async def test_copilot_run_agent_unknown_agent_error_event(client, auth_headers):
    engine = _CopilotEngine(intent='{"action":"run_agent","params":{"agent_key":"nope"}}')
    _use_engine(engine)
    try:
        r = await client.post(
            "/api/copilot/chat",
            json={"messages": [{"role": "user", "content": "运行不存在的智能体"}]},
            headers=auth_headers,
        )
        assert r.status_code == 200
        assert '"code": "agent_not_found"' in r.text
        assert '"type": "done"' in r.text
    finally:
        _drop_engine()


async def test_copilot_create_task_persists_scoped(client, auth_headers, db_session):
    proj = await client.post(
        "/api/projects", json={"name": "副驾测试项目"}, headers=auth_headers
    )
    pid = proj.json()["id"]
    engine = _CopilotEngine(
        intent=f'{{"action":"create_task","params":{{"project_id":"{pid}","title":"新任务","priority":"high"}}}}'
    )
    _use_engine(engine)
    try:
        r = await client.post(
            "/api/copilot/chat",
            json={"messages": [{"role": "user", "content": f"给 {pid} 建个高优任务"}]},
            headers=auth_headers,
        )
        assert r.status_code == 200
        assert '"kind": "task"' in r.text
        assert "新任务" in r.text
        assert '"type": "done"' in r.text
        rows = (await db_session.execute(select(Task))).scalars().all()
        assert len(rows) == 1
        assert rows[0].title == "新任务"
        assert rows[0].priority == "high"
    finally:
        _drop_engine()


async def test_copilot_cross_tenant_project_error_event(client, auth_headers, db_session):
    # 用户 A 建项目
    proj = await client.post(
        "/api/projects", json={"name": "A 的项目"}, headers=auth_headers
    )
    a_pid = proj.json()["id"]
    # 用户 B 注册
    r = await client.post(
        "/api/auth/register",
        json={"email": "b@example.com", "password": "secret123", "name": "B"},
    )
    b_headers = {"Authorization": f"Bearer {r.json()['access_token']}"}

    engine = _CopilotEngine(
        intent=f'{{"action":"create_task","params":{{"project_id":"{a_pid}","title":"越权任务"}}}}'
    )
    _use_engine(engine)
    try:
        resp = await client.post(
            "/api/copilot/chat",
            json={"messages": [{"role": "user", "content": "给 A 的项目建任务"}]},
            headers=b_headers,
        )
        assert resp.status_code == 200
        assert '"code": "project_not_found"' in resp.text
        assert '"type": "done"' in resp.text
        # 无脏数据：A 的项目下任务数仍为 0
        count = (
            await db_session.execute(
                select(func.count()).select_from(Task).where(Task.project_id == a_pid)
            )
        ).scalar_one()
        assert count == 0
    finally:
        _drop_engine()


async def test_copilot_engine_unavailable_error_event(client, auth_headers):
    engine = _CopilotEngine(fail_with=AiEngineUnavailable("AI 引擎未配置"))
    _use_engine(engine)
    try:
        r = await client.post(
            "/api/copilot/chat",
            json={"messages": [{"role": "user", "content": "你好"}]},
            headers=auth_headers,
        )
        # 全请求 200：引擎未配置走 error 事件而非 503（流已开始）
        assert r.status_code == 200
        assert '"code": "ai_unavailable"' in r.text
        assert '"type": "done"' in r.text
    finally:
        _drop_engine()


async def test_copilot_knowledge_no_match_short_circuit(client, auth_headers):
    proj = await client.post(
        "/api/projects", json={"name": "知识库测试"}, headers=auth_headers
    )
    pid = proj.json()["id"]
    engine = _CopilotEngine(
        intent=f'{{"action":"knowledge","params":{{"project_id":"{pid}"}}}}',
        outputs=["不应输出"],
    )
    _use_engine(engine)
    try:
        r = await client.post(
            "/api/copilot/chat",
            json={"messages": [{"role": "user", "content": "部署流程是什么"}]},
            headers=auth_headers,
        )
        assert r.status_code == 200
        assert "未找到" in r.text
        assert '"type": "done"' in r.text
        # 无检索命中时短路，不再调用 LLM 流式
        assert engine.stream_count == 0
    finally:
        _drop_engine()
