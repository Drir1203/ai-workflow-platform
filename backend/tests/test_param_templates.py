"""参数预置模板 API：按 user 隔离的命名参数模板 CRUD。"""


async def _create_template(client, headers, **overrides) -> dict:
    """创建一个模板，返回响应体。"""
    payload = {
        "name": "研发组周报",
        "agent_key": "weekly_report",
        "params": {"period": "this_week", "project_id": "p-1"},
    }
    payload.update(overrides)
    r = await client.post("/api/param-templates", json=payload, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()


async def test_create_and_list_templates(client, auth_headers):
    created = await _create_template(client, auth_headers)
    assert created["id"]
    assert created["name"] == "研发组周报"
    assert created["agent_key"] == "weekly_report"
    assert created["params"] == {"period": "this_week", "project_id": "p-1"}
    assert created["created_at"]

    r = await client.get("/api/param-templates", headers=auth_headers)
    assert r.status_code == 200
    items = r.json()
    assert len(items) == 1
    assert items[0]["id"] == created["id"]


async def test_list_templates_filtered_by_agent_key(client, auth_headers):
    await _create_template(client, auth_headers, name="周报模板", agent_key="weekly_report")
    await _create_template(client, auth_headers, name="巡检模板", agent_key="inspection_report")

    r = await client.get(
        "/api/param-templates?agent_key=weekly_report", headers=auth_headers
    )
    assert r.status_code == 200
    items = r.json()
    assert len(items) == 1
    assert items[0]["name"] == "周报模板"


async def test_update_template(client, auth_headers):
    created = await _create_template(client, auth_headers)

    r = await client.patch(
        f"/api/param-templates/{created['id']}",
        json={"name": "改名模板", "params": {"period": "last_week"}},
        headers=auth_headers,
    )
    assert r.status_code == 200
    body = r.json()
    assert body["name"] == "改名模板"
    assert body["params"] == {"period": "last_week"}
    assert body["agent_key"] == "weekly_report"  # 未改字段保持


async def test_delete_template(client, auth_headers):
    created = await _create_template(client, auth_headers)
    r = await client.delete(f"/api/param-templates/{created['id']}", headers=auth_headers)
    assert r.status_code == 204
    r = await client.get("/api/param-templates", headers=auth_headers)
    assert r.json() == []


async def test_update_delete_denied_for_other_user(client, auth_headers):
    created = await _create_template(client, auth_headers)

    r = await client.post(
        "/api/auth/register",
        json={"email": "b@example.com", "password": "secret123", "name": "B"},
    )
    assert r.status_code == 201
    headers_b = {"Authorization": f"Bearer {r.json()['access_token']}"}

    r = await client.patch(
        f"/api/param-templates/{created['id']}", json={"name": "越权"}, headers=headers_b
    )
    assert r.status_code == 404
    r = await client.delete(f"/api/param-templates/{created['id']}", headers=headers_b)
    assert r.status_code == 404


async def test_list_scoped_to_user(client, auth_headers):
    await _create_template(client, auth_headers)

    r = await client.post(
        "/api/auth/register",
        json={"email": "c@example.com", "password": "secret123", "name": "C"},
    )
    headers_c = {"Authorization": f"Bearer {r.json()['access_token']}"}

    # 其他用户看不到 A 的模板
    r = await client.get("/api/param-templates", headers=headers_c)
    assert r.json() == []


async def test_create_requires_name(client, auth_headers):
    r = await client.post(
        "/api/param-templates",
        json={"name": "", "agent_key": "weekly_report", "params": {}},
        headers=auth_headers,
    )
    assert r.status_code == 422


async def test_requires_auth(client):
    r = await client.get("/api/param-templates")
    assert r.status_code == 401
