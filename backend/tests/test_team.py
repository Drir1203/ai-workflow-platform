"""团队管理 + 角色权限测试：邀请链路、租户共享、readonly 写拦截、移除成员。"""

from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.models.invite import Invite


async def _register(client, email: str, name: str = "用户", invite_code: str | None = None) -> dict:
    """注册并返回 Bearer headers；带 invite_code 时验证进团队租户。"""
    payload = {"email": email, "password": "secret123", "name": name}
    if invite_code:
        payload["invite_code"] = invite_code
    r = await client.post("/api/auth/register", json=payload)
    assert r.status_code == 201, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


async def _create_invite(client, headers: dict, email: str, role: str = "member") -> str:
    """owner 创建邀请并返回 code。"""
    r = await client.post("/api/team/invites", json={"email": email, "role": role}, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()["code"]


async def test_team_requires_auth(client):
    r = await client.get("/api/team/members")
    assert r.status_code == 401


async def test_default_register_role_is_owner(client):
    r = await client.post(
        "/api/auth/register",
        json={"email": "boss@example.com", "password": "secret123", "name": "老板"},
    )
    assert r.status_code == 201
    assert r.json()["user"]["role"] == "owner"


async def test_register_with_invite_joins_team(client, auth_headers, db_session):
    """带邀请码注册：进入 owner 共享租户、继承 invited role、invite 标记已用。"""
    code = await _create_invite(client, auth_headers, "mate@example.com", "member")
    mate = await _register(client, "mate@example.com", "队友", invite_code=code)
    assert mate["Authorization"]

    r = await client.get("/api/team/members", headers=auth_headers)
    assert r.status_code == 200
    emails = [m["email"] for m in r.json()]
    assert "test@example.com" in emails and "mate@example.com" in emails

    invite = (
        await db_session.execute(select(Invite).where(Invite.code == code))
    ).scalar_one()
    assert invite.used_at is not None


async def test_invite_expired_or_wrong_code_rejected(client, auth_headers, db_session):
    # 过期：把 expires_at 改为过去再注册
    code = await _create_invite(client, auth_headers, "late@example.com", "member")
    invite = (
        await db_session.execute(select(Invite).where(Invite.code == code))
    ).scalar_one()
    invite.expires_at = datetime.now(timezone.utc) - timedelta(days=1)
    await db_session.commit()

    r = await client.post(
        "/api/auth/register",
        json={"email": "late@example.com", "password": "secret123", "name": "迟到者", "invite_code": code},
    )
    assert r.status_code == 400

    # 邮箱不匹配
    code2 = await _create_invite(client, auth_headers, "who@example.com", "member")
    r = await client.post(
        "/api/auth/register",
        json={"email": "else@example.com", "password": "secret123", "name": "路人", "invite_code": code2},
    )
    assert r.status_code == 400

    # 不存在 / 已用的 code
    r = await client.post(
        "/api/auth/register",
        json={"email": "ghost@example.com", "password": "secret123", "name": "幽灵", "invite_code": "no-such-code"},
    )
    assert r.status_code == 400


async def test_existing_user_accept_invite(client, auth_headers):
    """已注册用户凭 code 加入团队：租户变更后与 owner 数据互通。"""
    stranger = await _register(client, "stranger@example.com", "外人")
    code = await _create_invite(client, auth_headers, "stranger@example.com", "readonly")

    r = await client.post("/api/team/invites/accept", json={"code": code}, headers=stranger)
    assert r.status_code == 200
    assert r.json()["role"] == "readonly"

    # 迁入后 owner 成员列表可见
    r = await client.get("/api/team/members", headers=auth_headers)
    emails = [m["email"] for m in r.json()]
    assert "stranger@example.com" in emails


async def test_non_owner_cannot_manage_team(client, auth_headers):
    """member 无管理权：发邀请 / 改角色 / 移除 → 403。"""
    code = await _create_invite(client, auth_headers, "worker@example.com", "member")
    worker = await _register(client, "worker@example.com", "成员", invite_code=code)

    assert (await client.post("/api/team/invites", json={"email": "x@example.com", "role": "member"}, headers=worker)).status_code == 403

    r = await client.get("/api/team/members", headers=auth_headers)
    owner_id = next(m["id"] for m in r.json() if m["email"] == "test@example.com")
    assert (await client.patch(f"/api/team/members/{owner_id}", json={"role": "readonly"}, headers=worker)).status_code == 403
    assert (await client.delete(f"/api/team/members/{owner_id}", headers=worker)).status_code == 403


async def test_cannot_manage_outside_tenant(client, auth_headers):
    """跨租户改角色/移除 → 404（IDOR 防护）。"""
    stranger = await _register(client, "outsider@example.com", "外人")
    r = await client.get("/api/team/members", headers=stranger)
    outsider_id = r.json()[0]["id"]
    assert (
        await client.patch(f"/api/team/members/{outsider_id}", json={"role": "readonly"}, headers=auth_headers)
    ).status_code == 404


async def test_readonly_blocked_from_writes(client, auth_headers):
    """readonly 对 projects/tasks 写全部 403，读取保持 200；member 正常写。"""
    # owner 建一个项目，供 readonly 尝试改/删
    r = await client.post("/api/projects", json={"name": "团队项目"}, headers=auth_headers)
    pid = r.json()["id"]

    readonly_code = await _create_invite(client, auth_headers, "viewer@example.com", "readonly")
    viewer = await _register(client, "viewer@example.com", "只读者", invite_code=readonly_code)
    member_code = await _create_invite(client, auth_headers, "editor@example.com", "member")
    editor = await _register(client, "editor@example.com", "编辑者", invite_code=member_code)

    # readonly：create/update/delete 全 403
    assert (
        await client.post("/api/projects", json={"name": "越权"}, headers=viewer)
    ).status_code == 403
    assert (
        await client.post("/api/tasks", json={"project_id": pid, "title": "t"}, headers=viewer)
    ).status_code == 403
    assert (
        await client.patch(f"/api/projects/{pid}", json={"status": "archived"}, headers=viewer)
    ).status_code == 403
    assert (await client.delete(f"/api/projects/{pid}", headers=viewer)).status_code == 403

    # readonly：读取正常（可见团队数据）
    r = await client.get("/api/projects", headers=viewer)
    assert r.status_code == 200
    assert len(r.json()) == 1

    # member：正常写
    assert (
        await client.post("/api/projects", json={"name": "编辑者项目"}, headers=editor)
    ).status_code == 201


async def test_remove_member_exits_shared_tenant(client, auth_headers):
    """移除成员 = 迁出共享租户：owner 列表不再包含，被移除者工作台清空。"""
    code = await _create_invite(client, auth_headers, "leaver@example.com", "member")
    leaver = await _register(client, "leaver@example.com", "离开者", invite_code=code)
    await client.post("/api/projects", json={"name": "离开者项目"}, headers=leaver)

    r = await client.get("/api/team/members", headers=auth_headers)
    leaver_id = next(m["id"] for m in r.json() if m["email"] == "leaver@example.com")
    assert (await client.delete(f"/api/team/members/{leaver_id}", headers=auth_headers)).status_code == 204

    # owner 列表清空；被移除者回到独立租户（看不到团队数据，原数据也看不见）
    r = await client.get("/api/team/members", headers=auth_headers)
    assert "leaver@example.com" not in [m["email"] for m in r.json()]
    r = await client.get("/api/projects", headers=leaver)
    assert r.status_code == 200
    assert r.json() == []
