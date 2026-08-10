from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import ai, auth, health, notes, projects, tasks, wechat
from .config import settings
from .db import engine
from .models import Base


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # MVP：启动时建表（幂等）。生产环境后续替换为 Alembic 迁移。
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)

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
