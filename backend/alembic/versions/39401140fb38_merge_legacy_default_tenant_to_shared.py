"""merge legacy default tenant to shared

Revision ID: 39401140fb38
Revises: 7d2a9f4e3c1b8a50
Create Date: 2026-08-22 23:11:01.042971

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '39401140fb38'
down_revision: Union[str, Sequence[str], None] = '7d2a9f4e3c1b8a50'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# R17 数据隔离：存量用户与数据原先都挂在 `default` 租户下，而新注册用户
# 从 R17 起分配独立 uuid 租户。项目/任务/笔记等表没有 user_id，无法按用户
# 拆分存量数据，因此把 default 整体合并为一个共享租户（legacy-shared）：
# 存量用户之间保持互见（维持现状），但与所有新注册用户天然隔离。
LEGACY_TENANT = "legacy-shared"
_LEGACY_TABLES = (
    "users",
    "projects",
    "tasks",
    "notes",
    "workflows",
    "workflow_runs",
    "agent_runs",
    "custom_agents",
    "param_templates",
    "documents",
    "document_chunks",
    "wechat_subscriptions",
)


def _merge_tenant(table: str, target: str) -> None:
    """把表内所有 `default` 租户行迁移到目标租户（幂等：无 default 行则无操作）。"""
    op.get_bind().execute(
        sa.text(f"UPDATE {table} SET tenant_id = :target WHERE tenant_id = 'default'"),
        {"target": target},
    )


def upgrade() -> None:
    """Upgrade schema."""
    # 存量数据：default → legacy-shared 共享租户
    for table in _LEGACY_TABLES:
        _merge_tenant(table, LEGACY_TENANT)


def downgrade() -> None:
    """Downgrade schema."""
    # 回退：legacy-shared → default（仅供本地回滚，新注册的独立租户不受影响）
    for table in _LEGACY_TABLES:
        op.get_bind().execute(
            sa.text(f"UPDATE {table} SET tenant_id = 'default' WHERE tenant_id = :target"),
            {"target": LEGACY_TENANT},
        )
