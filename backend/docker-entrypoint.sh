#!/bin/sh
# AI智序 - Backend container entrypoint
# 启动前应用数据库迁移（幂等：已在 head 时是 no-op），再启动 uvicorn。
set -e

echo "Applying database migrations (alembic upgrade head)..."
alembic upgrade head

echo "Starting AI智序 backend..."
exec "$@"
