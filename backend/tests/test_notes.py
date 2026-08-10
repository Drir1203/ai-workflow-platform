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
