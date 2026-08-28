"""add user role and invites table

Revision ID: c3d4e5f6a7b8
Revises: 50151ff507e7
Create Date: 2026-08-28 09:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, Sequence[str], None] = '50151ff507e7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """团队权限：users 加租户级 role；新建 invites 表（owner 邀请他人加入共享租户）。"""
    # 存量用户一律 owner（保持现有「每人独立租户」语义不回归）；新注册仍默认 owner
    op.add_column(
        'users',
        sa.Column('role', sa.String(length=20), server_default='owner', nullable=False),
    )
    op.create_table(
        'invites',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('tenant_id', sa.String(length=36), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('role', sa.String(length=20), server_default='member', nullable=False),
        sa.Column('code', sa.String(length=64), nullable=False),
        sa.Column('inviter_id', sa.String(length=36), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_invites_code'), 'invites', ['code'], unique=True)
    op.create_index(op.f('ix_invites_tenant_id'), 'invites', ['tenant_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_invites_tenant_id'), table_name='invites')
    op.drop_index(op.f('ix_invites_code'), table_name='invites')
    op.drop_table('invites')
    op.drop_column('users', 'role')
