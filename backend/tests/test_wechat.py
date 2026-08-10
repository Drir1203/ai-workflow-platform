from datetime import date, timedelta

from app.api import wechat as wechat_api
from app.wechat.errors import WechatConfigError


async def _make_project(client, headers, name: str = "测试项目") -> str:
    r = await client.post("/api/projects", json={"name": name}, headers=headers)
    assert r.status_code == 201
    return r.json()["id"]


async def _make_task(client, headers, project_id: str, title: str = "任务", due=None) -> str:
    body = {"project_id": project_id, "title": title}
    if due is not None:
        body["due_date"] = due.isoformat()
    r = await client.post("/api/tasks", json=body, headers=headers)
    assert r.status_code == 201
    return r.json()["id"]


async def _bind_sub(client, headers, task_id: str, monkeypatch, openid: str = "openid_test"):
    async def fake_code2session(code: str) -> str:
        return openid

    monkeypatch.setattr(wechat_api, "code2session", fake_code2session)
    r = await client.post(
        "/api/wechat/subscribe",
        json={"code": "wx-code", "task_id": task_id, "template_id": "tpl_due"},
        headers=headers,
    )
    assert r.status_code == 200
    return r


async def test_subscribe_requires_auth(client):
    r = await client.post("/api/wechat/subscribe", json={"code": "x", "task_id": "x"})
    assert r.status_code == 401


async def test_subscribe_success(client, auth_headers, monkeypatch):
    pid = await _make_project(client, auth_headers)
    tid = await _make_task(client, auth_headers, pid)
    r = await _bind_sub(client, auth_headers, tid, monkeypatch)
    assert r.json()["status"] == "subscribed"


async def test_subscribe_task_not_found(client, auth_headers, monkeypatch):
    async def fake_code2session(code: str) -> str:
        return "openid_test"

    monkeypatch.setattr(wechat_api, "code2session", fake_code2session)
    r = await client.post(
        "/api/wechat/subscribe",
        json={"code": "x", "task_id": "no-such-task", "template_id": "tpl_due"},
        headers=auth_headers,
    )
    assert r.status_code == 404


async def test_subscribe_missing_template(client, auth_headers, monkeypatch):
    async def fake_code2session(code: str) -> str:
        return "openid_test"

    monkeypatch.setattr(wechat_api, "code2session", fake_code2session)
    monkeypatch.setattr(wechat_api.settings, "wechat_template_due", "")
    pid = await _make_project(client, auth_headers)
    tid = await _make_task(client, auth_headers, pid)
    r = await client.post(
        "/api/wechat/subscribe", json={"code": "x", "task_id": tid}, headers=auth_headers
    )
    assert r.status_code == 400


async def test_subscribe_wechat_unconfigured(client, auth_headers, monkeypatch):
    async def fail_code2session(code: str) -> str:
        raise WechatConfigError("微信未配置")

    monkeypatch.setattr(wechat_api, "code2session", fail_code2session)
    pid = await _make_project(client, auth_headers)
    tid = await _make_task(client, auth_headers, pid)
    r = await client.post(
        "/api/wechat/subscribe",
        json={"code": "x", "task_id": tid, "template_id": "tpl_due"},
        headers=auth_headers,
    )
    assert r.status_code == 503
    assert "未配置" in r.json()["detail"]


async def test_send_reminders_due_task(client, auth_headers, monkeypatch):
    sent: list[dict] = []

    async def fake_send(openid, template_id, page, data):
        sent.append({"openid": openid, "template_id": template_id, "page": page, "data": data})

    pid = await _make_project(client, auth_headers)
    tid = await _make_task(client, auth_headers, pid, due=date.today())
    await _bind_sub(client, auth_headers, tid, monkeypatch)
    monkeypatch.setattr(wechat_api, "send_subscribe_message", fake_send)

    r = await client.post("/api/wechat/reminders/send", headers=auth_headers)
    assert r.status_code == 200
    assert r.json() == {"sent": 1, "skipped": 0}
    assert len(sent) == 1
    assert sent[0]["data"]["thing1"]["value"] == "任务"
    assert sent[0]["page"] == f"pages/project/index?project_id={pid}"

    # 一次性：发送后再次触发不再重复发送
    r2 = await client.post("/api/wechat/reminders/send", headers=auth_headers)
    assert r2.json()["sent"] == 0


async def test_send_reminders_skips_future(client, auth_headers, monkeypatch):
    sent: list[str] = []

    async def fake_send(openid, template_id, page, data):
        sent.append(openid)

    pid = await _make_project(client, auth_headers)
    tid = await _make_task(client, auth_headers, pid, due=date.today() + timedelta(days=1))
    await _bind_sub(client, auth_headers, tid, monkeypatch)
    monkeypatch.setattr(wechat_api, "send_subscribe_message", fake_send)

    r = await client.post("/api/wechat/reminders/send", headers=auth_headers)
    assert r.json() == {"sent": 0, "skipped": 0}
    assert sent == []


async def test_send_reminders_skips_done(client, auth_headers, monkeypatch):
    async def fake_send(openid, template_id, page, data):
        raise AssertionError("不应发送已完成任务")

    pid = await _make_project(client, auth_headers)
    tid = await _make_task(client, auth_headers, pid, due=date.today())
    await _bind_sub(client, auth_headers, tid, monkeypatch)
    monkeypatch.setattr(wechat_api, "send_subscribe_message", fake_send)
    r = await client.patch(f"/api/tasks/{tid}", json={"status": "done"}, headers=auth_headers)
    assert r.status_code == 200

    r2 = await client.post("/api/wechat/reminders/send", headers=auth_headers)
    assert r2.json() == {"sent": 0, "skipped": 0}


async def test_send_reminders_wechat_error(client, auth_headers, monkeypatch):
    async def fail_send(openid, template_id, page, data):
        raise WechatConfigError("发送失败")

    pid = await _make_project(client, auth_headers)
    tid = await _make_task(client, auth_headers, pid, due=date.today())
    await _bind_sub(client, auth_headers, tid, monkeypatch)
    monkeypatch.setattr(wechat_api, "send_subscribe_message", fail_send)

    r = await client.post("/api/wechat/reminders/send", headers=auth_headers)
    assert r.json() == {"sent": 0, "skipped": 1}
