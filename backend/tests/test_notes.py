async def _make_project(client, headers, name="CrossBorder AI"):
    r = await client.post("/api/projects", json={"name": name}, headers=headers)
    assert r.status_code == 201
    return r.json()["id"]


async def test_create_and_list_notes(client, auth_headers):
    pid = await _make_project(client, auth_headers)
    r = await client.post(
        "/api/notes",
        json={"project_id": pid, "title": "巡检要点", "content": "1688 数据源巡检清单"},
        headers=auth_headers,
    )
    assert r.status_code == 201
    note = r.json()
    assert note["title"] == "巡检要点"
    assert note["content"] == "1688 数据源巡检清单"
    nid = note["id"]

    r = await client.get(f"/api/notes?project_id={pid}", headers=auth_headers)
    assert r.status_code == 200
    assert len(r.json()) == 1

    r = await client.get(f"/api/notes/{nid}", headers=auth_headers)
    assert r.status_code == 200


async def test_note_lifecycle(client, auth_headers):
    pid = await _make_project(client, auth_headers)
    r = await client.post("/api/notes", json={"project_id": pid, "title": "草稿"}, headers=auth_headers)
    nid = r.json()["id"]

    r = await client.patch(f"/api/notes/{nid}", json={"content": "已更新内容"}, headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["content"] == "已更新内容"

    r = await client.delete(f"/api/notes/{nid}", headers=auth_headers)
    assert r.status_code == 204

    r = await client.get(f"/api/notes/{nid}", headers=auth_headers)
    assert r.status_code == 404


async def test_note_requires_existing_project(client, auth_headers):
    r = await client.post("/api/notes", json={"project_id": "nope", "title": "孤立笔记"}, headers=auth_headers)
    assert r.status_code == 404


async def test_notes_require_auth(client):
    r = await client.get("/api/notes")
    assert r.status_code == 401


async def test_notes_isolated_between_users(client, auth_headers):
    """数据隔离：B 看不到/改不了 A 的笔记，也不能往 A 的项目下串建笔记。"""
    pid = await _make_project(client, auth_headers)
    r = await client.post(
        "/api/notes", json={"project_id": pid, "title": "A 的笔记"}, headers=auth_headers
    )
    assert r.status_code == 201
    nid = r.json()["id"]

    r = await client.post(
        "/api/auth/register",
        json={"email": "other@example.com", "password": "secret123", "name": "乙"},
    )
    headers2 = {"Authorization": f"Bearer {r.json()['access_token']}"}

    # B 的列表为空（全局 + 按 A 项目 id 均查不到）
    assert (await client.get("/api/notes", headers=headers2)).json() == []
    assert (
        await client.get(f"/api/notes?project_id={pid}", headers=headers2)
    ).json() == []

    # B 对 A 笔记 读/改/删 一律 404
    assert (await client.get(f"/api/notes/{nid}", headers=headers2)).status_code == 404
    assert (
        await client.patch(f"/api/notes/{nid}", json={"content": "越权改"}, headers=headers2)
    ).status_code == 404
    assert (await client.delete(f"/api/notes/{nid}", headers=headers2)).status_code == 404

    # B 不能往 A 的项目下建笔记（项目归属校验）
    r = await client.post(
        "/api/notes", json={"project_id": pid, "title": "越权笔记"}, headers=headers2
    )
    assert r.status_code == 404
