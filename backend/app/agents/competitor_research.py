from __future__ import annotations

from .base import Agent, AgentContext, AgentParam, AgentToolError
from .tools import fetch_url


class CompetitorResearchAgent:
    key = "competitor_research"
    name = "竞品调研"
    description = "抓取指定资料页面进行竞品分析；未提供 URL 时基于主题做通用分析"
    param_schema = [
        AgentParam("topic", "调研主题", required=True, placeholder="如：AI 项目管理工具"),
        AgentParam("urls", "资料 URL（每行一个）", type="textarea", required=False),
        AgentParam("max_sources", "抓取上限", type="number", default=3),
    ]

    async def run(self, ctx: AgentContext, params: dict) -> str:
        topic = (params.get("topic") or "").strip()
        if not topic:
            raise AgentToolError("请填写调研主题")

        raw_urls = (params.get("urls") or "").strip()
        urls = [u.strip() for u in raw_urls.splitlines() if u.strip()]
        try:
            max_sources = max(1, int(params.get("max_sources") or 3))
        except (TypeError, ValueError):
            max_sources = 3

        # 单 URL 抓取失败记录后跳过，不使整个运行致命
        fetch_errors: list[str] = []
        sources: list[str] = []
        for url in urls[:max_sources]:
            try:
                text = await fetch_url(url)
            except Exception as exc:  # noqa: BLE001 - 单来源失败不应中断整体调研
                fetch_errors.append(f"{url}: {exc}")
                continue
            if text:
                sources.append(f"## 来源 {url}\n{text}")

        error_note = ""
        if fetch_errors:
            error_note = "\n以下 URL 抓取失败（已跳过）：\n" + "\n".join(f"- {e}" for e in fetch_errors)

        if sources:
            query = f"""你是行业分析师。请基于以下抓取资料，对「{topic}」进行竞品调研，输出 Markdown。

要求：
- 按「概览 / 竞品对比 / 优势与不足 / 机会点 / 结论」五部分组织。
- 结论只基于资料内容，不要引入未提供的信息；资料不足处明确标注「资料有限」。
- 末尾附资料来源 URL 列表。

【抓取资料】
{chr(10).join(sources)}
{error_note}"""
        else:
            query = f"""你是行业分析师。对「{topic}」进行竞品调研，输出 Markdown。

注意：本次未提供可用的资料页面，请基于你的知识做通用分析，并在开头明确标注
「⚠️ 本次未抓取到资料，以下为基于主题的通用分析，建议补充资料后复核」。

要求：按「概览 / 常见竞品格局 / 关键能力对比 / 机会点 / 结论」组织。{error_note}"""
        return await ctx.chat(query)
