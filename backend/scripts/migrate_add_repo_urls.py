"""一次性幂等迁移：给 projects 表补充 L1 真实项目连接字段。

create_all 不会给已存在的表加列，需手动 ALTER。本脚本可重复执行，
已存在的列自动跳过。

用法：python scripts/migrate_add_repo_urls.py
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import text  # noqa: E402

from app.db import engine  # noqa: E402

NEW_COLUMNS = {
    "repo_url": "VARCHAR(300)",
    "deploy_url": "VARCHAR(300)",
    "local_path": "VARCHAR(300)",
}


async def migrate() -> None:
    async with engine.connect() as conn:
        rows = (await conn.execute(text("PRAGMA table_info(projects)"))).fetchall()
        existing = {row[1] for row in rows}
        for col, ddl in NEW_COLUMNS.items():
            if col in existing:
                print(f"[skip] projects.{col} 已存在")
                continue
            await conn.execute(text(f"ALTER TABLE projects ADD COLUMN {col} {ddl}"))
            print(f"[ok]   projects.{col} 已添加")
        await conn.commit()


if __name__ == "__main__":
    asyncio.run(migrate())
