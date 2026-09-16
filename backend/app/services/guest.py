"""访客体验账号：免注册进入共享演示租户，并附一份预置样例数据。

背景：把部署地址给面试官 / 访客时，对方没有账号会直接卡在登录页。这里提供
固定访客入口（POST /api/auth/guest）：后端保证访客账号与样例数据存在，前端
一键登录。

几个刻意的取舍：

- 密码列非空，写一段随机值。访客只能走 /api/auth/guest 换 token，拿不到也用
  不了这个口令 —— 前端 bundle 里因此不需要出现任何密码字面量。
- 角色给 member 而非 readonly。readonly 会让访客点「新建项目」时吃 403，演示
  现场看起来像平台坏了；member 可用全部业务功能，但 owner_only（发邀请 /
  改角色 / 移除成员）拿不到，即使被滥用也扩不出去。
- 样例数据在「该租户名下没有项目时」补齐，而不是仅在首次建号时种一次：访客把
  演示数据删空后，下一个访客仍能看到完整演示。反过来，只要还有项目就不动它，
  避免演示进行到一半被意外重置。
"""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..core.security import hash_password
from ..models.note import Note
from ..models.project import Project
from ..models.task import Task
from ..models.user import User

GUEST_EMAIL = "guest@veyawork.work"
GUEST_NAME = "访客"
# 固定租户 id（String(36)）：访客之间共享同一份演示数据，重置时按它清理
GUEST_TENANT_ID = "guest-demo-tenant"


async def ensure_guest(db: AsyncSession) -> User:
    """取访客账号；不存在则建号，并在租户无项目时补齐样例数据。"""
    user = (
        await db.execute(select(User).where(User.email == GUEST_EMAIL))
    ).scalar_one_or_none()

    if user is None:
        user = User(
            email=GUEST_EMAIL,
            # 随机口令：访客一律走 /api/auth/guest 换 token，这个哈希永远不会被校验成功
            password_hash=hash_password(secrets.token_urlsafe(32)),
            name=GUEST_NAME,
            tenant_id=GUEST_TENANT_ID,
            role="member",
        )
        db.add(user)
        await db.flush()

    await _seed_if_empty(db, user.tenant_id)
    await db.commit()
    await db.refresh(user)
    return user


async def _seed_if_empty(db: AsyncSession, tenant_id: str) -> None:
    """租户下没有项目时种入演示数据；已有数据则原样返回（不重置）。"""
    existing = (
        await db.execute(
            select(func.count()).select_from(Project).where(Project.tenant_id == tenant_id)
        )
    ).scalar_one()
    if existing:
        return

    # 用调度时区取「今天」，避免容器跑 UTC 时到期日整体偏一天
    today = datetime.now(ZoneInfo(settings.scheduler_timezone)).date()

    engine = Project(
        tenant_id=tenant_id,
        name="跨境选品决策引擎",
        description="面向跨境卖家的 AI 选品与合规预检：抓取竞品数据 → 智能体产出选品报告 → 定时工作流推送。",
        status="active",
        color="#BE903E",
        repo_url="https://github.com/Drir1203/crossborder-ai",
    )
    platform = Project(
        tenant_id=tenant_id,
        name="VeyaWork 雅秩平台",
        description="本平台自身：项目 / 任务 / 笔记工作台 + AI 副驾 + 多智能体编排 + 定时工作流。",
        status="active",
        color="#8AA670",
    )
    growth = Project(
        tenant_id=tenant_id,
        name="内容增长自动化",
        description="周报生成与多平台分发的自动化流水线（试运行中）。",
        status="paused",
        color="#8A9CA8",
    )
    db.add_all([engine, platform, growth])
    await db.flush()  # 回填 id（默认值为 Python 端 uuid4），下面任务/笔记要挂 project_id

    db.add_all(
        [
            # 跨境选品决策引擎
            Task(
                tenant_id=tenant_id,
                project_id=engine.id,
                title="接入竞品价格抓取工具",
                description="给智能体挂 fetch_url，抓取竞品页面价格与评分后回填报告。",
                priority="high",
                status="in_progress",
                due_date=today + timedelta(days=2),
            ),
            Task(
                tenant_id=tenant_id,
                project_id=engine.id,
                title="选品评分模型接入真实数据",
                description="把示例权重换成基于历史销量的回归系数。",
                priority="high",
                status="todo",
                due_date=today + timedelta(days=5),
            ),
            Task(
                tenant_id=tenant_id,
                project_id=engine.id,
                title="合规预检规则库整理",
                description="整理欧盟 / 北美主要品类的准入规则，转成结构化校验项。",
                priority="medium",
                status="todo",
            ),
            Task(
                tenant_id=tenant_id,
                project_id=engine.id,
                title="竞品数据抓取链路打通",
                description="代理池 + 失败重试，解决目标站点限流。",
                priority="medium",
                status="done",
            ),
            # VeyaWork 雅秩平台
            Task(
                tenant_id=tenant_id,
                project_id=platform.id,
                title="AI 副驾接入 SSE 流式输出",
                description="首字节即返回，逐字渲染，跨境链路上体感差异明显。",
                priority="high",
                status="done",
            ),
            Task(
                tenant_id=tenant_id,
                project_id=platform.id,
                title="补齐知识库问答引用溯源",
                description="回答中标注命中的文档片段，便于核对。",
                priority="medium",
                status="in_progress",
                due_date=today + timedelta(days=3),
            ),
            Task(
                tenant_id=tenant_id,
                project_id=platform.id,
                title="移动端导航适配",
                priority="low",
                status="todo",
            ),
            # 内容增长自动化
            Task(
                tenant_id=tenant_id,
                project_id=growth.id,
                title="周报模板参数化",
                description="把统计周期、项目范围做成工作流参数，支持按周/按月复用。",
                priority="medium",
                status="todo",
            ),
            Task(
                tenant_id=tenant_id,
                project_id=growth.id,
                title="多平台分发通道对接",
                priority="low",
                status="todo",
            ),
        ]
    )

    db.add_all(
        [
            Note(
                tenant_id=tenant_id,
                project_id=platform.id,
                title="架构速记",
                content=(
                    "## 分层\n\n"
                    "- **接入层**：FastAPI，AI 能力统一走 SSE 流式返回\n"
                    "- **编排层**：智能体 Runner / 工作流执行器，各自持有独立会话\n"
                    "- **数据层**：全部实体带 `tenant_id`，查询按租户过滤\n\n"
                    "## 三条不变量\n\n"
                    "1. 任何查询都必须带 `tenant_id`，否则会跨租户串数据\n"
                    "2. 后台任务自开会话，绝不共享请求级会话\n"
                    "3. 工作流调度器全进程单例，多 worker 部署前必须换分布式锁\n"
                ),
            ),
            Note(
                tenant_id=tenant_id,
                project_id=engine.id,
                title="选品评分维度",
                content=(
                    "按当前权重排序（待回归校准）：\n\n"
                    "| 维度 | 权重 | 数据来源 |\n"
                    "| --- | --- | --- |\n"
                    "| 需求量 | 30% | 关键词搜索量 |\n"
                    "| 竞争度 | 25% | 在售 Listing 数与评分分布 |\n"
                    "| 毛利空间 | 25% | 采购价 / 平台佣金反推 |\n"
                    "| 合规风险 | 20% | 准入规则库命中情况 |\n"
                ),
            ),
            Note(
                tenant_id=tenant_id,
                project_id=growth.id,
                title="第一期试运行结论",
                content=(
                    "> 结论：模板化能省掉 80% 的排版时间，但数据填充仍需人工确认。\n\n"
                    "**下一步**：把「取数 → 成文 → 分发」拆成三个可独立重试的工作流步骤，"
                    "避免最后一步失败要整条重跑。\n"
                ),
            ),
        ]
    )
    await db.flush()
