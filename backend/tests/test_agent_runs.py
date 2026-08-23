import asyncio

import pytest


class _FakeEngine:
    """后台引擎替身：返回固定回答。"""

    def __init__(self, answer: str = "后台回答"):
        self.answer = answer

    async def chat(self, query: str, user: str = "unknown") -> str:
        return self.answer

    async def knowledge_query(self, query: str, user: str = "unknown") -> str:
        return self.answer


class _RaisingEngine(_FakeEngine):
    async def chat(self, query: str, user: str = "unknown") -> str:
        raise RuntimeError("AI 服务故障")


async def _wait_run(client, headers, run_id, timeout: float = 3.0) -> dict:
    """轮询 run 直到终止态。"""
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


async def test_list_agents(client, auth_headers):
    r = await client.get("/api/agents", headers=auth_headers)
    assert r.status_code == 200
    keys = {a["key"] for a in r.json()}
    assert keys == {"weekly_report", "inspection_report", "interview_questions", "competitor_research"}


async def test_run_agent_requires_auth(client):
    r = await client.post("/api/agents/weekly_report/run", json={})
    assert r.status_code == 401


async def test_run_agent_unknown_key(client, auth_headers):
    r = await client.post("/api/agents/nope/run", json={}, headers=auth_headers)
    assert r.status_code == 404


async def test_run_agent_unknown_project(client, auth_headers):
    r = await client.post(
        "/api/agents/weekly_report/run",
        json={"project_id": "nope", "params": {}},
        headers=auth_headers,
    )
    assert r.status_code == 404


async def test_run_agent_and_poll_success(client, auth_headers, monkeypatch):
    monkeypatch.setattr("app.agents.runner.get_ai_engine", lambda: _FakeEngine("周报内容"))
    r = await client.post(
        "/api/agents/weekly_report/run",
        json={"params": {"period": "this_week"}},
        headers=auth_headers,
    )
    assert r.status_code == 202
    body = r.json()
    assert body["status"] == "pending"

    data = await _wait_run(client, auth_headers, body["run_id"])
    assert data["status"] == "succeeded"
    assert data["output"] == "周报内容"
    assert data["agent_key"] == "weekly_report"
    assert data["error"] is None


async def test_run_agent_failure_records_error(client, auth_headers, monkeypatch):
    monkeypatch.setattr("app.agents.runner.get_ai_engine", lambda: _RaisingEngine())
    r = await client.post(
        "/api/agents/interview_questions/run",
        json={"params": {"topic": "x"}},
        headers=auth_headers,
    )
    assert r.status_code == 202
    data = await _wait_run(client, auth_headers, r.json()["run_id"])
    assert data["status"] == "failed"
    assert "AI 服务故障" in data["error"]


async def test_list_runs_scoped_and_paginated(client, auth_headers, monkeypatch):
    monkeypatch.setattr("app.agents.runner.get_ai_engine", lambda: _FakeEngine())
    run_ids = []
    for i in range(3):
        r = await client.post(
            "/api/agents/interview_questions/run",
            json={"params": {"topic": f"t{i}"}},
            headers=auth_headers,
        )
        run_ids.append(r.json()["run_id"])
    for rid in run_ids:
        await _wait_run(client, auth_headers, rid)

    r = await client.get("/api/agents/runs?page_size=2", headers=auth_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 3
    assert len(body["items"]) == 2
    assert body["page"] == 1

    # agent_key 过滤
    r = await client.get(
        "/api/agents/runs?agent_key=weekly_report", headers=auth_headers
    )
    assert r.json()["total"] == 0


async def test_get_run_denied_for_other_user(client, auth_headers, monkeypatch):
    monkeypatch.setattr("app.agents.runner.get_ai_engine", lambda: _FakeEngine())
    r = await client.post("/api/agents/weekly_report/run", json={}, headers=auth_headers)
    run_id = r.json()["run_id"]
    await _wait_run(client, auth_headers, run_id)

    r = await client.post(
        "/api/auth/register",
        json={"email": "b@example.com", "password": "secret123", "name": "B"},
    )
    assert r.status_code == 201
    headers_b = {"Authorization": f"Bearer {r.json()['access_token']}"}

    r = await client.get(f"/api/agents/runs/{run_id}", headers=headers_b)
    assert r.status_code == 404

    # B 的运行记录列表也看不到 A 的记录（租户隔离）
    r = await client.get("/api/agents/runs", headers=headers_b)
    assert r.json()["total"] == 0


async def test_run_agent_cross_tenant_project_404(client, auth_headers, monkeypatch):
    """数据隔离 R17：不能把 run 挂到他人租户的项目下（项目归属校验）。"""
    r = await client.post("/api/projects", json={"name": "A 的项目"}, headers=auth_headers)
    pid = r.json()["id"]

    r = await client.post(
        "/api/auth/register",
        json={"email": "b@example.com", "password": "secret123", "name": "B"},
    )
    headers_b = {"Authorization": f"Bearer {r.json()['access_token']}"}

    r = await client.post(
        "/api/agents/weekly_report/run",
        json={"project_id": pid, "params": {}},
        headers=headers_b,
    )
    assert r.status_code == 404
