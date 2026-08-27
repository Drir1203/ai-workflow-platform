from sqlalchemy import func, select

from app.models.doc import Doc


async def _make_project(client, headers, name="CrossBorder AI"):
    r = await client.post("/api/projects", json={"name": name}, headers=headers)
    assert r.status_code == 201
    return r.json()["id"]


async def test_create_and_list_docs(client, auth_headers):
    pid = await _make_project(client, auth_headers)
    r = await client.post(
        "/api/docs",
        json={"project_id": pid, "title": "部署指南", "content": "# 部署\n\n一键 Docker Compose 私有化"},
        headers=auth_headers,
    )
    assert r.status_code == 201
    doc = r.json()
    assert doc["title"] == "部署指南"
    assert doc["content"].startswith("# 部署")
    assert doc["doc_meta"] is None
    did = doc["id"]

    r = await client.get(f"/api/docs?project_id={pid}", headers=auth_headers)
    assert r.status_code == 200
    assert len(r.json()) == 1

    r = await client.get(f"/api/docs/{did}", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["title"] == "部署指南"


async def test_doc_lifecycle(client, auth_headers):
    pid = await _make_project(client, auth_headers)
    r = await client.post("/api/docs", json={"project_id": pid, "title": "草稿"}, headers=auth_headers)
    did = r.json()["id"]

    r = await client.patch(f"/api/docs/{did}", json={"content": "已更新内容"}, headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["content"] == "已更新内容"

    r = await client.delete(f"/api/docs/{did}", headers=auth_headers)
    assert r.status_code == 204

    r = await client.get(f"/api/docs/{did}", headers=auth_headers)
    assert r.status_code == 404


async def test_doc_requires_existing_project(client, auth_headers):
    r = await client.post("/api/docs", json={"project_id": "nope", "title": "孤立文档"}, headers=auth_headers)
    assert r.status_code == 404


async def test_docs_require_auth(client):
    r = await client.get("/api/docs")
    assert r.status_code == 401


async def test_docs_isolated_between_users(client, auth_headers):
    """数据隔离：B 看不到/改不了 A 的文档，也不能往 A 的项目下串建文档。"""
    pid = await _make_project(client, auth_headers)
    r = await client.post(
        "/api/docs", json={"project_id": pid, "title": "A 的文档"}, headers=auth_headers
    )
    assert r.status_code == 201
    did = r.json()["id"]

    r = await client.post(
        "/api/auth/register",
        json={"email": "other2@example.com", "password": "secret123", "name": "乙"},
    )
    headers2 = {"Authorization": f"Bearer {r.json()['access_token']}"}

    # B 的列表为空（全局 + 按 A 项目 id 均查不到）
    assert (await client.get("/api/docs", headers=headers2)).json() == []
    assert (
        await client.get(f"/api/docs?project_id={pid}", headers=headers2)
    ).json() == []

    # B 对 A 文档 读/改/删 一律 404
    assert (await client.get(f"/api/docs/{did}", headers=headers2)).status_code == 404
    assert (
        await client.patch(f"/api/docs/{did}", json={"content": "越权改"}, headers=headers2)
    ).status_code == 404
    assert (await client.delete(f"/api/docs/{did}", headers=headers2)).status_code == 404

    # B 不能往 A 的项目下建文档（项目归属校验）
    r = await client.post(
        "/api/docs", json={"project_id": pid, "title": "越权文档"}, headers=headers2
    )
    assert r.status_code == 404


async def test_delete_project_cascades_docs(client, auth_headers, db_session):
    """删项目后 docs 无残留（应用层级联，SQLite 不强制外键）。"""
    pid = await _make_project(client, auth_headers)
    await client.post("/api/docs", json={"project_id": pid, "title": "待级联"}, headers=auth_headers)
    r = await client.delete(f"/api/projects/{pid}", headers=auth_headers)
    assert r.status_code == 204
    count = (
        await db_session.execute(
            select(func.count()).select_from(Doc).where(Doc.project_id == pid)
        )
    ).scalar_one()
    assert count == 0
