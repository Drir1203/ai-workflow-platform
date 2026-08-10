import time

import httpx

from ..config import settings
from .errors import WechatConfigError

WECHAT_API = "https://api.weixin.qq.com"

# 进程内缓存 access_token（微信有效期 7200s，提前 300s 刷新）
_token_cache: dict[str, object] = {"token": None, "expires_at": 0.0}


def _require_config() -> None:
    if not settings.wechat_appid or not settings.wechat_secret:
        raise WechatConfigError("微信未配置（WECHAT_APPID / WECHAT_SECRET 为空）")


async def get_access_token() -> str:
    """获取微信 access_token（缓存 + 提前刷新）。"""
    _require_config()
    now = time.time()
    if _token_cache["token"] and _token_cache["expires_at"] > now + 300:
        return str(_token_cache["token"])
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(
            f"{WECHAT_API}/cgi-bin/token",
            params={
                "grant_type": "client_credential",
                "appid": settings.wechat_appid,
                "secret": settings.wechat_secret,
            },
        )
        resp.raise_for_status()
        data = resp.json()
    if "access_token" not in data:
        raise WechatConfigError(f"获取 access_token 失败：{data.get('errmsg', data)}")
    _token_cache["token"] = data["access_token"]
    _token_cache["expires_at"] = now + int(data.get("expires_in", 7200))
    return str(_token_cache["token"])


async def code2session(code: str) -> str:
    """wx.login 的 code → openid（用于绑定订阅）。"""
    _require_config()
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(
            f"{WECHAT_API}/sns/jscode2session",
            params={
                "appid": settings.wechat_appid,
                "secret": settings.wechat_secret,
                "js_code": code,
                "grant_type": "authorization_code",
            },
        )
        resp.raise_for_status()
        data = resp.json()
    openid = data.get("openid")
    if not openid:
        raise WechatConfigError(f"jscode2session 失败：{data.get('errmsg', data)}")
    return openid


async def send_subscribe_message(
    openid: str, template_id: str, page: str, data: dict[str, dict[str, str]]
) -> dict:
    """发送一条订阅消息。data 形如 {"thing1": {"value": "任务标题"}, ...}。"""
    token = await get_access_token()
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            f"{WECHAT_API}/cgi-bin/message/subscribe/send",
            params={"access_token": token},
            json={
                "touser": openid,
                "template_id": template_id,
                "page": page,
                "data": data,
                "miniprogram_state": "developer",
            },
        )
        resp.raise_for_status()
        body = resp.json()
    if body.get("errcode", 0) != 0:
        raise WechatConfigError(f"订阅消息发送失败：{body.get('errmsg', body)}")
    return body
