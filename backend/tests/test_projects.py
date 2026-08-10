async def test_create_and_list_projects(client, auth_headers):
    r = await client.post(
        "/api/projects",
        json={
            "name": "CrossBorder AI",
            "description": "1688 数据源",
            "color": "#D9A441",
            "repo_url": "https://github.com/Drir1203/crossborder-ai",
            "deploy_url": None,
            "local_path": "d:/work/crossborder-ai",
        },
        headers=auth_headers,
    )
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == "CrossBorder AI"
    assert data["status"] == "active"
    assert data["repo_url"] == "https://github.com/Drir1203/crossborder-ai"
    assert data["deploy_url"] is None
    assert data["local_path"] == "d:/work/crossborder-ai"
    pid = data["id"]

    r = await client.get("/api/projects", headers=auth_headers)
    assert r.status_code == 200
    assert len(r.json()) == 1

    r = await client.get(f"/api/projects/{pid}", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["description"] == "1688 数据源"


async def test_update_and_delete(client, auth_headers):
    r = await client.post("/api/projects", json={"name": "面试教练"}, headers=auth_headers)
    pid = r.json()["id"]

    r = await client.patch(
        f"/api/projects/{pid}", json={"status": "archived", "color": "#E8C078"}, headers=auth_headers
    )
    assert r.status_code == 200
    assert r.json()["status"] == "archived"

    r = await client.delete(f"/api/projects/{pid}", headers=auth_headers)
    assert r.status_code == 204

    r = await client.get(f"/api/projects/{pid}", headers=auth_headers)
    assert r.status_code == 404


async def test_projects_require_auth(client):
    r = await client.get("/api/projects")
    assert r.status_code == 401


async def test_project_not_found(client, auth_headers):
    r = await client.get("/api/projects/nope", headers=auth_headers)
    assert r.status_code == 404
