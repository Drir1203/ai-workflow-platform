from __future__ import annotations

import asyncio
import ipaddress
import re
import socket
import urllib.parse

import httpx

from app.config import settings


def _is_unsafe_ip(host: str) -> bool:
    """判断 IP 字面量是否命中私有/保留/链路本地/组播/未指定地址。"""
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return False
    return (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    )


async def _is_safe_host(hostname: str) -> bool:
    """hostname 安全校验：IP 字面量直接判断；域名解析后逐 IP 检查（任一不安全即拒绝）。

    用 loop.getaddrinfo（线程池执行）避免阻塞事件循环。
    """
    if _is_unsafe_ip(hostname):
        return False
    loop = asyncio.get_running_loop()
    try:
        infos = await loop.getaddrinfo(hostname, None)
    except socket.gaierror:
        return False
    seen: set[str] = set()
    for info in infos:
        ip = info[4][0]
        if ip in seen:
            continue
        seen.add(ip)
        if _is_unsafe_ip(ip):
            return False
    return True


async def is_safe_url(url: str) -> bool:
    """SSRF 防护：仅放行 http(s)、无凭据、目标不在私有/保留地址段的 URL。

    注：校验与 fetch 是两次独立 DNS 解析，存在 DNS rebinding 间隙（已接受风险：
    URL 由登录用户自供，且单机部署无内网服务可探）。彻底消除需解析后 pin IP 连接。
    """
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return False
    if not parsed.hostname:
        return False
    if parsed.username or parsed.password:
        return False
    return await _is_safe_host(parsed.hostname)


def _strip_html(raw: str) -> str:
    """去除 HTML 标签与脚本内容，保留文本。"""
    text = re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", raw)
    text = re.sub(r"(?is)<[^>]+>", " ", text)
    text = (
        text.replace("&nbsp;", " ")
        .replace("&amp;", "&")
        .replace("&lt;", "<")
        .replace("&gt;", ">")
        .replace("&quot;", '"')
        .replace("&#39;", "'")
    )
    return text


async def _read_body(resp: httpx.Response) -> str:
    """流式读取响应体：按字节硬上限截断后去标签、压缩空白。

    httpx 的 get 不预缓冲 body，必须在 client 上下文内读完；同时限流避免恶意源灌满内存。
    """
    max_bytes = settings.agent_fetch_max_chars * 4 + 4096  # 字符上限×4（多字节 UTF-8）+ 余量
    raw = b""
    async for chunk in resp.aiter_bytes():
        raw += chunk
        if len(raw) > max_bytes:
            break
    text = _strip_html(raw.decode(resp.encoding or "utf-8", errors="replace"))
    text = re.sub(r"\s+", " ", text).strip()
    return text[: settings.agent_fetch_max_chars]


async def fetch_url(url: str) -> str:
    """抓取网页正文（去标签、压缩空白），截断到 agent_fetch_max_chars。

    重定向逐跳校验目标（SSRF 防护不因跳转而绕过），最多 5 次跳转。
    """
    current = url
    seen: set[str] = set()
    async with httpx.AsyncClient(timeout=settings.agent_fetch_timeout) as client:
        for _ in range(5):
            if current in seen:
                raise ValueError("检测到重定向循环")
            seen.add(current)
            if not await is_safe_url(current):
                raise ValueError("不允许访问的 URL（SSRF 防护）")
            resp = await client.get(
                current,
                headers={"User-Agent": "ProjectHub-Agent/1.0"},
                follow_redirects=False,
            )
            if resp.status_code in (301, 302, 303, 307, 308):
                location = resp.headers.get("location")
                if not location:
                    return ""
                current = str(httpx.URL(current).join(location))
                continue
            resp.raise_for_status()
            return await _read_body(resp)
        raise ValueError("重定向次数过多")
