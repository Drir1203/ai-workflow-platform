# ProjectHub AI - Backend Dockerfile
# 多阶段构建：依赖层 → 运行时层（仿 VeyaShip 模式，pyproject.toml 构建）

# ════════════════════════════════════════════════════════════════
# 第一阶段：依赖安装
# ════════════════════════════════════════════════════════════════
FROM python:3.12-slim AS deps

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_INDEX_URL=https://mirrors.aliyun.com/pypi/simple/

# 编译 PostgreSQL 驱动需要 gcc + libpq-dev
# 国内服务器（阿里云 ECS）构建加速：apt 源切换为阿里云镜像。
# 海外部署时删除下面两行 sed 即可回到官方源。
RUN sed -i 's|http://deb.debian.org/debian|http://mirrors.aliyun.com/debian|g' \
        /etc/apt/sources.list.d/debian.sources /etc/apt/sources.list 2>/dev/null || true \
    && sed -i 's|http://security.debian.org/debian-security|http://mirrors.aliyun.com/debian-security|g' \
        /etc/apt/sources.list.d/debian.sources /etc/apt/sources.list 2>/dev/null || true \
    && apt-get update && apt-get install -y --no-install-recommends \
        gcc \
        libpq-dev \
        curl \
    && rm -rf /var/lib/apt/lists/*

# 先拷 pyproject.toml + 应用代码再装依赖——利用 Docker 层缓存
COPY pyproject.toml ./
COPY app ./app
RUN pip install --upgrade pip \
    && pip install --no-cache-dir .

# ════════════════════════════════════════════════════════════════
# 第二阶段：运行镜像
# ════════════════════════════════════════════════════════════════
FROM python:3.12-slim AS runtime

WORKDIR /app

# 从 deps 阶段复制已安装的 Python 包与可执行文件
COPY --from=deps /usr/local/lib/python3.12/site-packages/ /usr/local/lib/python3.12/site-packages/
COPY --from=deps /usr/local/bin/ /usr/local/bin/

# 应用代码 + Alembic 迁移（alembic 不是包，必须显式拷贝）
COPY app ./app
COPY alembic.ini .
COPY alembic ./alembic

# 入口：启动前先跑迁移
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh

# 非 root 用户运行（安全最佳实践）
RUN addgroup --system --gid 1001 app \
    && adduser --system --uid 1001 --ingroup app app \
    && chown -R app:app /app \
    && chmod +x /usr/local/bin/docker-entrypoint.sh

USER app

EXPOSE 8000

ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
