"""AI 副驾核心编排：意图解析 → 分发 → SSE 事件流。

事件协议（router 序列化为 ``data: {json}\\n\\n``）：
  {"type":"status", "message": str, "agent"?: {key,name}, "workflow"?: {id,name}}
  {"type":"text",   "delta": str}                          # 流式增量
  {"type":"result", "kind": "agent"|"workflow"|"task"|"project"|"knowledge", "data": {...}}
  {"type":"done"}
  {"type":"error",  "code": str, "message": str}           # 后跟 done

多租户：所有查询/创建都按 user.tenant_id 过滤，project/workflow 归属校验与
既有 API 一致（跨租户一律当作不存在，IDOR 防护）。
"""

from __future__ import annotations

import asyncio
import json
import re
from collections.abc import AsyncIterator
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base import AgentContext
from app.agents.custom import CustomAgentExecutor, resolve_agent, validate_params
from app.agents.registry import AGENT_REGISTRY, ensure_registered
from app.config import settings
from app.models.agent_run import AgentRun
from app.models.custom_agent import CustomAgent
from app.models.project import Project
from app.models.task import Task
from app.models.user import User
from app.models.workflow import Workflow
from app.models.workflow_run import WorkflowRun
from app.rag.prompts import build_qa_prompt
from app.rag.retriever import KeywordRetriever
from app.schemas.project import ProjectCreate
from app.schemas.task import TaskCreate
from app.workflows.executor import workflow_run_manager

from .prompts import build_intent_prompt

# 合法动作白名单：LLM 输出在名单外一律回退 answer（见 parse_intent）
_ACTION_SET = {"answer", "knowledge", "run_agent", "run_workflow", "create_task", "create_project", "help"}
_JSON_RE = re.compile(r"\{.*\}", re.S)


@dataclass
class Intent:
    """LLM 解析出的意图。"""

    action: str
    params: dict = field(default_factory=dict)
    need_params: list[str] = field(default_factory=list)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ── SSE 事件构造器 ──────────────────────────────────────────────

def event_status(message: str, agent: dict | None = None, workflow: dict | None = None) -> dict:
    ev: dict[str, Any] = {"type": "status", "message": message}
    if agent:
        ev["agent"] = agent
    if workflow:
        ev["workflow"] = workflow
    return ev


def event_text(delta: str) -> dict:
    return {"type": "text", "delta": delta}


def event_result(kind: str, data: dict) -> dict:
    return {"type": "result", "kind": kind, "data": data}


def event_done() -> dict:
    return {"type": "done"}


def event_error(code: str, message: str) -> dict:
    return {"type": "error", "code": code, "message": message}


# ── 意图解析 ────────────────────────────────────────────────────

def parse_intent(raw: str) -> Intent:
    """从 LLM 输出中提取意图 JSON；解析失败/动作非法一律回退 answer。

    用正则抓第一个 ``{...}``（LLM 偶尔会夹带解释文字），再 json 解析 + 白名单。
    """
    m = _JSON_RE.search(raw)
    if not m:
        return Intent(action="answer")
    try:
        data = json.loads(m.group(0))
    except json.JSONDecodeError:
        return Intent(action="answer")
    if not isinstance(data, dict):
        return Intent(action="answer")
    action = data.get("action")
    if action not in _ACTION_SET:
        return Intent(action="answer")
    return Intent(
        action=action,
        params=data.get("params") or {},
        need_params=data.get("need_params") or [],
    )


# ── 上下文构建（当前租户能力清单）───────────────────────────────

def _schema_to_prompt(field: dict) -> dict:
    """只保留意图路由需要的 schema 字段（剥掉 label/placeholder 省 token）。"""
    out: dict[str, Any] = {
        "name": field.get("name"),
        "type": field.get("type", "text"),
        "required": bool(field.get("required")),
    }
    options = field.get("options") or []
    if options:
        out["options"] = [
            o.get("value") for o in options if isinstance(o, dict) and o.get("value")
        ]
    return out


async def build_context(db: AsyncSession, user: User) -> dict:
    """聚合当前租户的智能体 / 工作流 / 项目清单，注入意图路由提示词。"""
    ensure_registered()
    agents: list[dict] = []
    for a in AGENT_REGISTRY.list():
        schema = [asdict(p) for p in a.param_schema]
        agents.append(
            {
                "key": a.key,
                "name": a.name,
                "description": a.description,
                "param_schema": [_schema_to_prompt(p) for p in schema],
            }
        )
    custom = (
        await db.execute(select(CustomAgent).where(CustomAgent.tenant_id == user.tenant_id))
    ).scalars().all()
    for a in custom:
        agents.append(
            {
                "key": a.key,
                "name": a.name,
                "description": a.description or "",
                "param_schema": [_schema_to_prompt(p) for p in (a.param_schema or [])],
            }
        )
    workflows = (
        await db.execute(select(Workflow).where(Workflow.tenant_id == user.tenant_id))
    ).scalars().all()
    projects = (
        await db.execute(select(Project).where(Project.tenant_id == user.tenant_id))
    ).scalars().all()
    return {
        "agents": agents,
        "workflows": [
            {"id": w.id, "name": w.name, "description": w.description or ""} for w in workflows
        ],
        "projects": [{"id": p.id, "name": p.name} for p in projects],
    }


async def classify_intent(engine, user: User, messages: list[dict], context: dict) -> Intent:
    """非流式 LLM 一次调用解析意图（同时注入租户能力清单）。"""
    raw = await engine.chat(build_intent_prompt(messages, context), user.id)
    return parse_intent(raw)


# ── 对话历史工具 ────────────────────────────────────────────────

def _last_user_text(messages: list[dict]) -> str:
    for m in reversed(messages):
        if m.get("role") == "user":
            return m.get("content", "")
    return ""


def _trim_history(messages: list[dict], limit: int | None = None) -> list[dict]:
    """上下文截断：只留最近 N 条，防止多轮膨胀超 token。"""
    n = limit or settings.copilot_max_history
    return messages[-n:] if len(messages) > n else messages


# ── 主分发 ──────────────────────────────────────────────────────

HELP_TEXT = """我是「雅秩」AI 副驾，可以用自然语言直接指挥平台干活：

- **写报告**：说「帮我写本周周报」或「生成巡检报告」，我会自动调度对应智能体；
- **问知识库**：说「部署流程是什么」，我会检索项目知识库并带来源回答；
- **跑工作流**：说「运行每日巡检工作流」；
- **建任务/项目**：说「创建高优任务：修复登录 bug（属于 xx 项目）」或「新建一个项目叫 xx」；
- **普通问答**：直接问我任何问题。

试试对我说「帮我写本周周报」吧！"""


async def stream_response(
    db: AsyncSession,
    user: User,
    engine,
    messages: list[dict],
    project_id: str | None = None,
) -> AsyncIterator[dict]:
    """副驾主流程：意图路由 → 分发 → 产出 SSE 事件序列。"""
    context = await build_context(db, user)
    intent = await classify_intent(engine, user, messages, context)

    # 意图缺参数：直接文字澄清，不再二次调 LLM（省成本）
    if intent.need_params:
        yield event_text("还需要你补充：{}".format("、".join(intent.need_params)))
        yield event_done()
        return

    action = intent.action
    if action == "help":
        yield event_text(HELP_TEXT)
        yield event_done()
        return
    if action == "answer":
        direct = (intent.params or {}).get("text")
        if direct:
            yield event_text(direct)
        else:
            async for chunk in engine.stream_chat(_trim_history(messages), user.id):
                yield event_text(chunk)
        yield event_done()
        return
    if action == "knowledge":
        async for ev in _handle_knowledge(db, user, engine, intent, messages, project_id):
            yield ev
        return
    if action == "run_agent":
        async for ev in _handle_run_agent(db, user, engine, intent):
            yield ev
        return
    if action == "run_workflow":
        async for ev in _handle_run_workflow(db, user, intent):
            yield ev
        return
    if action == "create_task":
        async for ev in _handle_create_task(db, user, intent):
            yield ev
        return
    if action == "create_project":
        async for ev in _handle_create_project(db, user, intent):
            yield ev
        return
    # 兜底：白名单之外的动作（正常不会走到）流式回答
    async for chunk in engine.stream_chat(_trim_history(messages), user.id):
        yield event_text(chunk)
    yield event_done()


# ── 各动作处理器 ────────────────────────────────────────────────

async def _handle_knowledge(
    db: AsyncSession,
    user: User,
    engine,
    intent: Intent,
    messages: list[dict],
    request_project_id: str | None,
) -> AsyncIterator[dict]:
    """知识库 RAG 问答：检索 + build_qa_prompt + 流式 + 附来源。"""
    q = _last_user_text(messages)
    pid = intent.params.get("project_id") or request_project_id
    if not pid:
        yield event_text("请问要检索哪个项目的知识库？告诉我项目名，或在对应项目页里打开副驾再问。")
        yield event_done()
        return
    project = await db.get(Project, pid)
    if project is None or project.tenant_id != user.tenant_id:
        yield event_error("project_not_found", "项目不存在或无权访问")
        yield event_done()
        return
    chunks = await KeywordRetriever(top_k=settings.rag_top_k).top_chunks(db, pid, q)
    if not chunks:
        yield event_text("知识库中未找到与「{}」相关的信息。".format(q))
        yield event_done()
        return
    yield event_status("正在检索「{}」知识库…".format(project.name))
    prompt = build_qa_prompt(q, chunks)
    async for chunk in engine.stream_chat(
        [*_trim_history(messages), {"role": "user", "content": prompt}], user.id
    ):
        yield event_text(chunk)
    yield event_result(
        "knowledge",
        {
            "query": q,
            "project_id": pid,
            "project_name": project.name,
            "sources": [
                {
                    "document_id": c.document_id,
                    "document_name": c.document_name,
                    "seq": c.seq,
                }
                for c in chunks
            ],
        },
    )
    yield event_done()


async def _handle_run_agent(db: AsyncSession, user: User, engine, intent: Intent) -> AsyncIterator[dict]:
    """运行智能体：同步 await agent.run，落 AgentRun 记录，结果导向。"""
    agent_key = intent.params.get("agent_key")
    agent = await resolve_agent(db, agent_key) if agent_key else None
    if agent is None:
        yield event_error("agent_not_found", "未找到该智能体")
        yield event_done()
        return
    # 自定义 Agent 仅限同租户执行（与 list_agents 可见范围一致），防跨租户猜 key
    if isinstance(agent, CustomAgentExecutor) and agent.agent.tenant_id != user.tenant_id:
        yield event_error("agent_not_found", "未找到该智能体")
        yield event_done()
        return
    # 参数 schema：内置 Agent 是 AgentParam dataclass，自定义 Agent 已是 list[dict]
    schema = agent.param_schema
    if schema and not isinstance(schema[0], dict):
        schema = [asdict(p) for p in schema]
    raw_params = intent.params.get("params") or {}
    try:
        cleaned = validate_params(schema, raw_params)
    except ValueError as exc:
        yield event_error("params_invalid", str(exc))
        yield event_done()
        return
    pid = raw_params.get("project_id")
    if pid:
        project = await db.get(Project, pid)
        if project is None or project.tenant_id != user.tenant_id:
            yield event_error("project_not_found", "项目不存在或无权访问")
            yield event_done()
            return
    yield event_status(
        "正在运行智能体「{}」".format(agent.name), agent={"key": agent.key, "name": agent.name}
    )

    run = AgentRun(
        user_id=user.id,
        tenant_id=user.tenant_id,
        agent_key=agent.key,
        status="running",
        params=cleaned,
        project_id=pid,
        started_at=_utcnow(),
    )
    db.add(run)
    await db.commit()
    await db.refresh(run)

    output: str | None = None
    error_ev: dict | None = None
    try:
        ctx = AgentContext(db=db, user=user, engine=engine, tenant_id=user.tenant_id)
        # 单次 LLM 缺口 <120s（nginx 读超时）；wait_for 兜底总时长防失控
        output = await asyncio.wait_for(agent.run(ctx, cleaned), timeout=settings.copilot_agent_timeout)
        run.output, run.status = output, "succeeded"
    except asyncio.TimeoutError:
        run.status, run.error = "failed", "运行超时"
        error_ev = event_error("agent_timeout", "智能体运行超时，请稍后重试")
    except asyncio.CancelledError:
        # 客户端断开流式连接：尽力把 run 置失败后重抛，让 FastAPI 收尾
        run.status, run.error = "failed", "客户端中断"
        run.finished_at = _utcnow()
        try:
            await db.commit()
        except Exception:
            pass
        raise
    except Exception as exc:
        run.status, run.error = "failed", str(exc)
        error_ev = event_error("agent_failed", "智能体运行失败：{}".format(exc))
    run.finished_at = _utcnow()
    await db.commit()

    if error_ev is not None:
        yield error_ev
    else:
        yield event_result(
            "agent",
            {
                "agent_key": agent.key,
                "name": agent.name,
                "run_id": run.id,
                "output": output,
            },
        )
    yield event_done()


async def _handle_run_workflow(db: AsyncSession, user: User, intent: Intent) -> AsyncIterator[dict]:
    """运行工作流：校验租户 → 落 WorkflowRun → 后台 submit + 返回 run_id。

    工作流多步多次 LLM 调用必超 120s，走后台执行；前端用既有 getWorkflowRun 轮询。
    """
    wf_id = intent.params.get("workflow_id")
    wf = await db.get(Workflow, wf_id) if wf_id else None
    if wf is None or wf.tenant_id != user.tenant_id:
        yield event_error("workflow_not_found", "未找到该工作流")
        yield event_done()
        return
    run = WorkflowRun(
        tenant_id=wf.tenant_id,
        workflow_id=wf.id,
        user_id=user.id,
        status="pending",
        triggered_by="manual",
    )
    db.add(run)
    await db.commit()
    await db.refresh(run)
    workflow_run_manager.submit(run.id)
    yield event_status(
        "已提交工作流「{}」，后台运行中".format(wf.name), workflow={"id": wf.id, "name": wf.name}
    )
    yield event_result(
        "workflow",
        {"run_id": run.id, "workflow_id": wf.id, "name": wf.name, "status": run.status},
    )
    yield event_done()


async def _handle_create_task(db: AsyncSession, user: User, intent: Intent) -> AsyncIterator[dict]:
    """创建任务：复用 TaskCreate pydantic 校验 + 项目租户校验 + 落库。"""
    params = intent.params or {}
    try:
        task_in = TaskCreate.model_validate(params)
    except Exception as exc:
        yield event_error("params_invalid", "任务参数不合法：{}".format(exc))
        yield event_done()
        return
    project = await db.get(Project, task_in.project_id)
    if project is None or project.tenant_id != user.tenant_id:
        yield event_error("project_not_found", "项目不存在或无权访问")
        yield event_done()
        return
    task = Task(**task_in.model_dump(), tenant_id=user.tenant_id)
    db.add(task)
    await db.commit()
    await db.refresh(task)
    yield event_status("已创建任务「{}」".format(task.title))
    yield event_result(
        "task",
        {
            "id": task.id,
            "title": task.title,
            "project_id": task.project_id,
            "project_name": project.name,
            "priority": task.priority,
            "status": task.status,
        },
    )
    yield event_done()


async def _handle_create_project(db: AsyncSession, user: User, intent: Intent) -> AsyncIterator[dict]:
    """创建项目：复用 ProjectCreate pydantic 校验 + 落库（租户随创建者注入）。"""
    params = intent.params or {}
    try:
        proj_in = ProjectCreate.model_validate(params)
    except Exception as exc:
        yield event_error("params_invalid", "项目参数不合法：{}".format(exc))
        yield event_done()
        return
    project = Project(**proj_in.model_dump(), tenant_id=user.tenant_id)
    db.add(project)
    await db.commit()
    await db.refresh(project)
    yield event_status("已创建项目「{}」".format(project.name))
    yield event_result(
        "project", {"id": project.id, "name": project.name, "status": project.status}
    )
    yield event_done()
