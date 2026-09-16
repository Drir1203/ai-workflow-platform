"""访客体验入口 /api/auth/guest 的行为约束。"""

from sqlalchemy import delete, select

from app.config import settings
from app.models import Project, Task
from app.services.guest import GUEST_EMAIL, GUEST_TENANT_ID


async def test_guest_login_creates_account_with_seeded_data(client):
    r = await client.post("/api/auth/guest")
    assert r.status_code == 200
    body = r.json()
    assert body["access_token"]
    assert body["user"]["email"] == GUEST_EMAIL
    # member 而非 readonly：访客要能用全部业务功能，只挡 owner 专属操作
    assert body["user"]["role"] == "member"

    headers = {"Authorization": f"Bearer {body['access_token']}"}
    projects = (await client.get("/api/projects", headers=headers)).json()
    assert len(projects) >= 2
    assert {p["name"] for p in projects} >= {"跨境选品决策引擎", "VeyaWork 雅秩平台"}

    # 任务必须挂在已种入的项目下，否则仪表盘统计会全空
    tasks = (await client.get("/api/tasks", headers=headers)).json()
    assert len(tasks) >= 5
    assert {t["project_id"] for t in tasks} <= {p["id"] for p in projects}


async def test_guest_login_is_idempotent(client):
    """重复进入复用同一账号与租户，不会每来一个访客就多建一份账号。"""
    first = (await client.post("/api/auth/guest")).json()["user"]
    second = (await client.post("/api/auth/guest")).json()["user"]
    assert first["id"] == second["id"]


async def test_guest_can_write_but_not_manage_team(client):
    token = (await client.post("/api/auth/guest")).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # member 可建项目（readonly 会 403，演示现场看起来像坏了）
    created = await client.post(
        "/api/projects", json={"name": "访客自建项目"}, headers=headers
    )
    assert created.status_code == 201

    # 但拿不到 owner 专属能力，被滥用也扩不出去
    invite = await client.post(
        "/api/team/invites",
        json={"email": "someone@example.com", "role": "member"},
        headers=headers,
    )
    assert invite.status_code == 403


async def test_guest_data_reseeds_after_wipe(client, db_session):
    """演示数据被删空后，下一个访客仍应看到完整演示（而非空平台）。"""
    token = (await client.post("/api/auth/guest")).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    await db_session.execute(delete(Project).where(Project.tenant_id == GUEST_TENANT_ID))
    await db_session.commit()
    assert (await client.get("/api/projects", headers=headers)).json() == []

    await client.post("/api/auth/guest")
    reseeded = (await client.get("/api/projects", headers=headers)).json()
    assert len(reseeded) >= 2
    # 补种只补项目不够，任务要一起回来
    task_count = (
        await db_session.execute(
            select(Task).where(Task.tenant_id == GUEST_TENANT_ID)
        )
    ).scalars().all()
    assert len(task_count) >= 5


async def test_guest_data_preserved_when_not_empty(client, db_session):
    """只要还有项目就不重置，避免演示进行到一半被意外清空。"""
    token = (await client.post("/api/auth/guest")).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    await client.post("/api/projects", json={"name": "半途加的项目"}, headers=headers)

    await client.post("/api/auth/guest")
    names = {p["name"] for p in (await client.get("/api/projects", headers=headers)).json()}
    assert "半途加的项目" in names


async def test_guest_entry_can_be_disabled(client, monkeypatch):
    monkeypatch.setattr(settings, "guest_access_enabled", False)
    assert (await client.post("/api/auth/guest")).status_code == 403


async def test_guest_random_password_is_unusable(client):
    """密码列是随机值，不应能用它登录走 login 通道。"""
    await client.post("/api/auth/guest")
    for guess in ("", "guest", "password", "veyawork"):
        r = await client.post(
            "/api/auth/login", json={"email": GUEST_EMAIL, "password": guess}
        )
        assert r.status_code == 401
