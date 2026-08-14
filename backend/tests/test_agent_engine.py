from datetime import datetime

import httpx
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.agents import AGENT_REGISTRY, ensure_registered
from app.agents.base import AgentContext, AgentToolError
from app.agents.competitor_research import CompetitorResearchAgent
from app.agents.inspection_report import InspectionReportAgent
from app.agents.interview_questions import InterviewQuestionsAgent
from app.agents.tools import fetch_url, is_safe_url
from app.agents.weekly_report import WeeklyReportAgent
from app.models import Base, Note, Project, Task, User


class _FakeEngine:
    """替代 AiEngine：记录查询并返回固定答案。"""

    def __init__(self, answer: str = "AI 输出"):
        self.answer = answer
        self.queries: list[str] = []

    async def chat(self, query: str, user: str = "unknown") -> str:
        self.queries.append(query)
        return self.answer

    async def knowledge_query(self, query: str, user: str = "unknown") -> str:
        return self.answer


@pytest_asyncio.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with factory() as db:
        yield db
    await engine.dispose()


@pytest_asyncio.fixture
async def seeded(session):
    now = datetime.now()
    user = User(id="u1", email="a@b.com", password_hash="x", name="tester")
    p1 = Project(id="p1", name="官网重构", status="active", description="新版官网")
    p2 = Project(id="p2", name="内部工具", status="active", description="内部效率工具")
    t1 = Task(
        id="t1", project_id="p1", title="首页改版", status="done", priority="high",
        description="完成首屏", created_at=now,
    )
    t2 = Task(
        id="t2", project_id="p1", title="移动端适配", status="in_progress",
        priority="medium", created_at=now,
    )
    t3 = Task(
        id="t3", project_id="p2", title="后台面板", status="todo", priority="low",
        created_at=now,
    )
    n1 = Note(id="n1", project_id="p1", title="设计评审", content="确定了新版配色")
    session.add_all([user, p1, p2, t1, t2, t3, n1])
    await session.commit()
    return {"session": session, "user": user, "tasks": [t1, t2, t3], "notes": [n1]}


def _make_ctx(session, user, engine=None):
    return AgentContext(db=session, user=user, engine=engine or _FakeEngine())


def test_registry_has_four_agents():
    ensure_registered()
    keys = {a.key for a in AGENT_REGISTRY.list()}
    assert keys == {"weekly_report", "inspection_report", "interview_questions", "competitor_research"}


def test_agent_param_schema_shape():
    ensure_registered()
    agent = AGENT_REGISTRY.get("weekly_report")
    assert agent is not None
    period = next(p for p in agent.param_schema if p.name == "period")
    assert period.type == "select"
    assert {o["value"] for o in period.options} == {"this_week", "last_week", "this_month"}
    topic = next(
        p for p in AGENT_REGISTRY.get("interview_questions").param_schema if p.name == "topic"
    )
    assert topic.required is True


async def test_weekly_report_builds_prompt(seeded):
    engine = _FakeEngine()
    ctx = _make_ctx(seeded["session"], seeded["user"], engine)
    out = await WeeklyReportAgent().run(ctx, {"period": "this_week"})
    assert out == "AI 输出"
    query = engine.queries[0]
    assert "周报" in query
    assert "官网重构" in query      # 项目上下文
    assert "首页改版" in query      # 任务上下文
    assert "设计评审" in query      # 笔记上下文


async def test_weekly_report_unknown_project_raises(seeded):
    ctx = _make_ctx(seeded["session"], seeded["user"])
    with pytest.raises(AgentToolError):
        await WeeklyReportAgent().run(ctx, {"period": "this_week", "project_id": "nope"})


async def test_inspection_report_stats(seeded):
    engine = _FakeEngine()
    ctx = _make_ctx(seeded["session"], seeded["user"], engine)
    out = await InspectionReportAgent().run(ctx, {"project_id": "p1"})
    assert out == "AI 输出"
    query = engine.queries[0]
    assert "完成率 50.0%" in query   # p1 共 2 任务，1 完成
    assert "官网重构" in query
    assert "高优先级未完成：0" in query


async def test_inspection_report_requires_project(seeded):
    ctx = _make_ctx(seeded["session"], seeded["user"])
    with pytest.raises(AgentToolError):
        await InspectionReportAgent().run(ctx, {})


async def test_inspection_report_missing_project_raises(seeded):
    ctx = _make_ctx(seeded["session"], seeded["user"])
    with pytest.raises(AgentToolError):
        await InspectionReportAgent().run(ctx, {"project_id": "nope"})


async def test_interview_questions_clamps_count(seeded):
    engine = _FakeEngine()
    ctx = _make_ctx(seeded["session"], seeded["user"], engine)
    await InterviewQuestionsAgent().run(ctx, {"topic": "FastAPI", "count": 99})
    assert "20 道" in engine.queries[-1]
    await InterviewQuestionsAgent().run(ctx, {"topic": "FastAPI", "count": 0})
    assert "1 道" in engine.queries[-1]
    await InterviewQuestionsAgent().run(ctx, {"topic": "FastAPI", "count": "abc"})
    assert "10 道" in engine.queries[-1]


async def test_interview_questions_requires_topic(seeded):
    ctx = _make_ctx(seeded["session"], seeded["user"])
    with pytest.raises(AgentToolError):
        await InterviewQuestionsAgent().run(ctx, {})


async def test_competitor_research_no_urls_generic(seeded):
    engine = _FakeEngine()
    ctx = _make_ctx(seeded["session"], seeded["user"], engine)
    await CompetitorResearchAgent().run(ctx, {"topic": "AI 项目管理"})
    assert "通用分析" in engine.queries[0]
    assert "AI 项目管理" in engine.queries[0]


async def test_competitor_research_skips_failed_url(seeded, monkeypatch):
    async def fake_fetch(url: str) -> str:
        if url == "https://bad.example/x":
            raise RuntimeError("timeout")
        return f"资料：{url}"

    monkeypatch.setattr("app.agents.competitor_research.fetch_url", fake_fetch)
    engine = _FakeEngine()
    ctx = _make_ctx(seeded["session"], seeded["user"], engine)
    urls = "https://bad.example/x\nhttps://good.example/y"
    await CompetitorResearchAgent().run(ctx, {"topic": "竞品A", "urls": urls})
    query = engine.queries[0]
    assert "资料：https://good.example/y" in query
    assert "https://bad.example/x: timeout" in query


# ---------- SSRF 防护（is_safe_url 纯函数） ----------

@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1/",
        "http://10.0.0.5/",
        "http://192.168.1.1/",
        "http://172.16.0.9/",
        "http://169.254.1.1/",
        "http://0.0.0.0/",
        "http://224.0.0.1/",
        "http://240.0.0.1/",
        "http://[::1]/",
        "http://[fe80::1]/",
        "http://[fc00::1]/",
        "ftp://example.com/",
        "http://user:pass@example.com/",
        "not-a-url",
    ],
)
async def test_is_safe_url_rejects_unsafe(url):
    assert await is_safe_url(url) is False


async def test_is_safe_url_accepts_public():
    assert await is_safe_url("https://93.184.216.34/") is True
    assert await is_safe_url("https://93.184.216.34:8080/page") is True


# ---------- fetch_url（monkeypatch httpx） ----------


class _FakeAsyncClient:
    """替代 httpx.AsyncClient：按响应列表依次返回。"""

    def __init__(self, responses):
        self.responses = list(responses)
        self.calls: list[str] = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def get(self, url, headers=None, follow_redirects=False):
        self.calls.append(url)
        return self.responses.pop(0)


def _resp(status, text="", headers=None):
    req = httpx.Request("GET", "http://x")
    return httpx.Response(status, text=text, headers=headers or {}, request=req)


async def test_fetch_url_strips_html(monkeypatch):
    html = (
        "<html><head><style>p{color:red}</style></head><body>"
        "<script>var x=1</script><h1>标题</h1><p>  正文内容   </p></body></html>"
    )
    fake = _FakeAsyncClient([_resp(200, html)])
    monkeypatch.setattr(httpx, "AsyncClient", lambda *a, **k: fake)
    text = await fetch_url("https://example.com/a")
    assert "标题" in text
    assert "正文内容" in text
    assert "script" not in text
    assert fake.calls[0] == "https://example.com/a"


async def test_fetch_url_truncates(monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "agent_fetch_max_chars", 10)
    fake = _FakeAsyncClient([_resp(200, "<p>abcdefghijklmnopqrstuvwxyz</p>")])
    monkeypatch.setattr(httpx, "AsyncClient", lambda *a, **k: fake)
    text = await fetch_url("https://example.com/a")
    assert len(text) <= 10


class _ChunkStream(httpx.AsyncByteStream):
    """分块响应流：模拟大响应体逐步到达，验证流式字节上限。"""

    def __init__(self, chunks: list[bytes]) -> None:
        self.chunks = chunks

    async def __aiter__(self):
        for c in self.chunks:
            yield c


def _resp_stream(status, chunks, headers=None):
    req = httpx.Request("GET", "http://x")
    return httpx.Response(status, headers=headers or {}, request=req, stream=_ChunkStream(chunks))


async def test_fetch_url_caps_body_bytes(monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "agent_fetch_max_chars", 100)
    big = b"x" * 20000
    fake = _FakeAsyncClient([_resp_stream(200, [big, big])])
    monkeypatch.setattr(httpx, "AsyncClient", lambda *a, **k: fake)
    text = await fetch_url("https://example.com/a")
    assert len(text) <= 100


async def test_fetch_url_follows_safe_redirect(monkeypatch):
    fake = _FakeAsyncClient([
        _resp(302, headers={"Location": "https://example.com/b"}),
        _resp(200, "<p>落地页</p>"),
    ])
    monkeypatch.setattr(httpx, "AsyncClient", lambda *a, **k: fake)
    text = await fetch_url("https://example.com/a")
    assert "落地页" in text
    assert fake.calls == ["https://example.com/a", "https://example.com/b"]


async def test_fetch_url_blocks_redirect_to_private(monkeypatch):
    fake = _FakeAsyncClient([_resp(302, headers={"Location": "http://127.0.0.1/secret"})])
    monkeypatch.setattr(httpx, "AsyncClient", lambda *a, **k: fake)
    with pytest.raises(ValueError):
        await fetch_url("https://example.com/a")
