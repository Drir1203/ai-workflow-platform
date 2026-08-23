async def _make_project(client, headers, name="CrossBorder AI"):
    r = await client.post("/api/projects", json={"name": name}, headers=headers)
    assert r.status_code == 201
    return r.json()["id"]


async def test_create_and_list_tasks(client, auth_headers):
    pid = await _make_project(client, auth_headers)
    r = await client.post(
        "/api/tasks",
        json={"project_id": pid, "title": "巡检 1688 商品数据源", "priority": "high"},
        headers=auth_headers,
    )
    assert r.status_code == 201
    task = r.json()
    assert task["title"] == "巡检 1688 商品数据源"
    assert task["priority"] == "high"
    assert task["status"] == "todo"

    r = await client.get(f"/api/tasks?project_id={pid}", headers=auth_headers)
    assert r.status_code == 200
    assert len(r.json()) == 1


async def test_task_lifecycle(client, auth_headers):
    pid = await _make_project(client, auth_headers)
    r = await client.post(
        "/api/tasks", json={"project_id": pid, "title": "更新押题题库 v3"}, headers=auth_headers
    )
    tid = r.json()["id"]

    r = await client.patch(f"/api/tasks/{tid}", json={"status": "done"}, headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["status"] == "done"

    r = await client.delete(f"/api/tasks/{tid}", headers=auth_headers)
    assert r.status_code == 204

    r = await client.get(f"/api/tasks/{tid}", headers=auth_headers)
    assert r.status_code == 404


async def test_task_requires_existing_project(client, auth_headers):
    r = await client.post(
        "/api/tasks", json={"project_id": "nope", "title": "孤立任务"}, headers=auth_headers
    )
    assert r.status_code == 404


async def test_tasks_require_auth(client):
    r = await client.post("/api/tasks", json={"project_id": "x", "title": "y"})
    assert r.status_code == 401


async def test_tasks_isolated_between_users(client, auth_headers):
    """数据隔离：B 看不到/改不了 A 的任务，也不能往 A 的项目下串建任务。"""
    pid = await _make_project(client, auth_headers)
    r = await client.post(
        "/api/tasks", json={"project_id": pid, "title": "A 的任务"}, headers=auth_headers
    )
    assert r.status_code == 201
    tid = r.json()["id"]

    r = await client.post(
        "/api/auth/register",
        json={"email": "other@example.com", "password": "secret123", "name": "乙"},
    )
    headers2 = {"Authorization": f"Bearer {r.json()['access_token']}"}

    # B 的列表为空（全局 + 按 A 项目 id 均查不到）
    assert (await client.get("/api/tasks", headers=headers2)).json() == []
    assert (
        await client.get(f"/api/tasks?project_id={pid}", headers=headers2)
    ).json() == []

    # B 对 A 任务 读/改/删 一律 404
    assert (await client.get(f"/api/tasks/{tid}", headers=headers2)).status_code == 404
    assert (
        await client.patch(f"/api/tasks/{tid}", json={"status": "done"}, headers=headers2)
    ).status_code == 404
    assert (await client.delete(f"/api/tasks/{tid}", headers=headers2)).status_code == 404

    # B 不能往 A 的项目下建任务（项目归属校验）
    r = await client.post(
        "/api/tasks", json={"project_id": pid, "title": "越权任务"}, headers=headers2
    )
    assert r.status_code == 404
