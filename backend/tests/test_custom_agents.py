"""自定义 Agent（DB 持久化）：CRUD、list 合并（source 标记）、{{param}} 渲染与执行。"""

import asyncio

import pytest


class _RecordingEngine:
    """记录最近一次 prompt，返回「回答: <prompt>」。"""

    def __init__(self) -> None:
        self.last_query: str | None = None

    async def chat(self, query: str, user: str = "unknown") -> str:
        self.last_query = query
        return f"回答: {query}"

    async def knowledge_query(self, query: str, user: str = "unknown") -> str:
        return query


async def _wait_run(client, headers, run_id, timeout: float = 3.0) -> dict:
    """轮询 agent run 直到终止态。"""
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout
    while True:
        r = await client.get(f"/api/agents/runs/{run_id}", headers=headers)
        assert r.status_code == 200
        data = r.json()
        if data["status"] in ("succeeded", "failed"):
            return data
        if loop.time() > deadline:
            raise AssertionError(f"run {run_id} 未在 {timeout}s 内结束: status={data['status']}")
        await asyncio.sleep(0.05)


async def _wait_workflow_run(client, headers, run_id, timeout: float = 3.0) -> dict:
    """轮询 workflow run 直到终止态。"""
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout
    while True:
        r = await client.get(f"/api/workflows/runs/{run_id}", headers=headers)
        assert r.status_code == 200
        data = r.json()
        if data["status"] in ("succeeded", "failed"):
            return data
        if loop.time() > deadline:
            raise AssertionError(f"run {run_id} 未在 {timeout}s 内结束: status={data['status']}")
        await asyncio.sleep(0.05)


async def _create_agent(client, headers, **overrides) -> dict:
    """创建自定义 Agent，返回响应体。"""
    payload = {
        "name": "测试助手",
        "description": "测试用",
        "prompt": "你是助手，请回答 {{topic}} 相关问题",
        "param_schema": [
            {
                "name": "topic",
                "label": "主题",
                "type": "text",
                "required": True,
                "default": None,
                "options": [],
                "placeholder": "",
            }
        ],
    }
    payload.update(overrides)
    r = await client.post("/api/agents", json=payload, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()


# ---------- CRUD ----------


async def test_create_custom_agent(client, auth_headers):
    body = await _create_agent(client, auth_headers)
    assert body["key"].startswith("custom-")
    assert body["name"] == "测试助手"
    assert body["prompt"].startswith("你是助手")
    assert body["param_schema"][0]["name"] == "topic"
    assert body["id"]


async def test_create_custom_agent_requires_prompt(client, auth_headers):
    r = await client.post(
        "/api/agents",
        json={"name": "无提示词", "description": "", "prompt": ""},
        headers=auth_headers,
    )
    assert r.status_code == 422


async def test_list_agents_marks_source(client, auth_headers):
    # 无自定义时，只有 4 个内置，source=builtin 且无 prompt
    r = await client.get("/api/agents", headers=auth_headers)
    assert r.status_code == 200
    items = r.json()
    assert len(items) == 4
    assert all(a["source"] == "builtin" for a in items)
    assert all(a.get("prompt") is None for a in items)

    # 建一个自定义后，合并进列表且带 prompt
    created = await _create_agent(client, auth_headers)
    r = await client.get("/api/agents", headers=auth_headers)
    custom = [a for a in r.json() if a["source"] == "custom"]
    assert len(custom) == 1
    assert custom[0]["key"] == created["key"]
    assert custom[0]["prompt"] == created["prompt"]


async def test_update_custom_agent(client, auth_headers):
    created = await _create_agent(client, auth_headers)
    r = await client.patch(
        f"/api/agents/{created['key']}",
        json={"name": "改名助手", "prompt": "新提示词 {{topic}}"},
        headers=auth_headers,
    )
    assert r.status_code == 200
    body = r.json()
    assert body["name"] == "改名助手"
    assert body["prompt"] == "新提示词 {{topic}}"
    assert body["description"] == "测试用"  # 未改字段保持不变


async def test_update_delete_denied_for_other_user(client, auth_headers):
    created = await _create_agent(client, auth_headers)

    r = await client.post(
        "/api/auth/register",
        json={"email": "b@example.com", "password": "secret123", "name": "B"},
    )
    assert r.status_code == 201
    headers_b = {"Authorization": f"Bearer {r.json()['access_token']}"}

    r = await client.patch(f"/api/agents/{created['key']}", json={"name": "越权"}, headers=headers_b)
    assert r.status_code == 404
    r = await client.delete(f"/api/agents/{created['key']}", headers=headers_b)
    assert r.status_code == 404


async def test_delete_custom_agent(client, auth_headers):
    created = await _create_agent(client, auth_headers)
    r = await client.delete(f"/api/agents/{created['key']}", headers=auth_headers)
    assert r.status_code == 204
    r = await client.get("/api/agents", headers=auth_headers)
    assert all(a["key"] != created["key"] for a in r.json())


# ---------- 执行 ----------


async def test_run_custom_agent_renders_prompt(client, auth_headers, monkeypatch):
    engine = _RecordingEngine()
    monkeypatch.setattr("app.agents.runner.get_ai_engine", lambda: engine)
    created = await _create_agent(client, auth_headers)

    r = await client.post(
        f"/api/agents/{created['key']}/run",
        json={"params": {"topic": "FastAPI"}},
        headers=auth_headers,
    )
    assert r.status_code == 202
    data = await _wait_run(client, auth_headers, r.json()["run_id"])
    assert data["status"] == "succeeded"
    assert engine.last_query == "你是助手，请回答 FastAPI 相关问题"
    assert data["output"] == "回答: 你是助手，请回答 FastAPI 相关问题"


async def test_run_custom_agent_missing_required_422(client, auth_headers, monkeypatch):
    monkeypatch.setattr("app.agents.runner.get_ai_engine", lambda: _RecordingEngine())
    created = await _create_agent(client, auth_headers)
    r = await client.post(
        f"/api/agents/{created['key']}/run", json={"params": {}}, headers=auth_headers
    )
    assert r.status_code == 422
    assert "缺少必填参数" in r.json()["detail"]


async def test_run_custom_agent_number_validation(client, auth_headers, monkeypatch):
    monkeypatch.setattr("app.agents.runner.get_ai_engine", lambda: _RecordingEngine())
    created = await _create_agent(
        client,
        auth_headers,
        prompt="数量 {{count}}",
        param_schema=[
            {
                "name": "count",
                "label": "数量",
                "type": "number",
                "required": True,
                "default": None,
                "options": [],
                "placeholder": "",
            }
        ],
    )
    r = await client.post(
        f"/api/agents/{created['key']}/run",
        json={"params": {"count": "abc"}},
        headers=auth_headers,
    )
    assert r.status_code == 422
    assert "需要数字" in r.json()["detail"]


# ---------- 工作流 / 定时调度集成（自定义步骤可执行） ----------


async def test_custom_agent_in_workflow(client, auth_headers, monkeypatch):
    engine = _RecordingEngine()
    monkeypatch.setattr("app.workflows.executor.get_ai_engine", lambda: engine)
    created = await _create_agent(client, auth_headers)

    r = await client.post(
        "/api/workflows",
        json={
            "name": "带自定义步骤",
            "steps": [
                {"label": "自定义", "agent_key": created["key"], "params": {"topic": "工作流主题"}}
            ],
        },
        headers=auth_headers,
    )
    assert r.status_code == 201, r.text
    wf_id = r.json()["id"]

    r = await client.post(f"/api/workflows/{wf_id}/run", headers=auth_headers)
    assert r.status_code == 202
    data = await _wait_workflow_run(client, auth_headers, r.json()["run_id"])
    assert data["status"] == "succeeded", data.get("error")
    assert data["results"][0]["agent_key"] == created["key"]
    assert engine.last_query == "你是助手，请回答 工作流主题 相关问题"


async def test_custom_agent_in_scheduled_trigger(client, auth_headers, monkeypatch):
    engine = _RecordingEngine()
    monkeypatch.setattr("app.workflows.executor.get_ai_engine", lambda: engine)
    created = await _create_agent(client, auth_headers)

    r = await client.post(
        "/api/workflows",
        json={
            "name": "定时自定义",
            "steps": [
                {"label": "自定义", "agent_key": created["key"], "params": {"topic": "定时主题"}}
            ],
            "schedule": {"cron": "0 9 * * 1"},
        },
        headers=auth_headers,
    )
    assert r.status_code == 201, r.text

    from app.workflows.scheduler import workflow_scheduler

    await workflow_scheduler._trigger(r.json()["id"])

    r = await client.get("/api/workflows/runs", headers=auth_headers)
    runs = r.json()["items"]
    assert len(runs) == 1
    data = await _wait_workflow_run(client, auth_headers, runs[0]["id"])
    assert data["status"] == "succeeded", data.get("error")
    assert engine.last_query == "你是助手，请回答 定时主题 相关问题"


# ---------- 校验行为（review 修复回归） ----------


def test_validate_params_preserves_int_and_drops_empty_optional():
    """number 参数保留 int 类型；schema 内可选空参数不补回字面 None/""。"""
    from app.agents.custom import validate_params

    schema = [
        {"name": "count", "label": "数量", "type": "number", "required": True},
        {"name": "note", "label": "备注", "type": "text", "required": False},
    ]
    cleaned = validate_params(schema, {"count": 42, "note": ""})
    assert cleaned == {"count": 42}
    assert cleaned["count"] == 42 and isinstance(cleaned["count"], int)

    # 字符串数字转 float；可选 None 丢弃
    cleaned2 = validate_params(schema, {"count": "3.5", "note": None})
    assert cleaned2 == {"count": 3.5}

    # bool 是 int 子类，明确拒绝
    with pytest.raises(ValueError):
        validate_params(schema, {"count": True})

    # 额外参数透传；schema 外的 None 丢弃
    cleaned3 = validate_params(schema, {"count": 1, "extra": "x", "junk": None})
    assert cleaned3 == {"count": 1, "extra": "x"}


async def test_run_shared_with_tenant_mate(client, auth_headers, monkeypatch):
    """同租户其他用户可运行自定义 Agent（团队共享模型，与 list_agents 可见范围一致）。"""
    engine = _RecordingEngine()
    monkeypatch.setattr("app.agents.runner.get_ai_engine", lambda: engine)
    created = await _create_agent(client, auth_headers)

    r = await client.post(
        "/api/auth/register",
        json={"email": "mate@example.com", "password": "secret123", "name": "同事"},
    )
    assert r.status_code == 201
    headers_mate = {"Authorization": f"Bearer {r.json()['access_token']}"}

    r = await client.post(
        f"/api/agents/{created['key']}/run",
        json={"params": {"topic": "共享主题"}},
        headers=headers_mate,
    )
    assert r.status_code == 202, r.text
    data = await _wait_run(client, headers_mate, r.json()["run_id"])
    assert data["status"] == "succeeded"
    assert engine.last_query == "你是助手，请回答 共享主题 相关问题"
