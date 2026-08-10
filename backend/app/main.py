from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import ai, auth, health, notes, projects, tasks, wechat
from .config import settings

# 数据库 Schema 由 Alembic 迁移管理（容器入口/部署脚本执行 `alembic upgrade head`），
# 不再在启动时 create_all，避免与迁移漂移。

app = FastAPI(title=settings.app_name, version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(projects.router)
app.include_router(tasks.router)
app.include_router(notes.router)
app.include_router(ai.router)
app.include_router(wechat.router)


@app.get("/")
async def root() -> dict[str, str]:
    return {"service": settings.app_name, "docs": "/docs"}
