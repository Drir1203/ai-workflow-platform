# AI智序 部署文档

阿里云 ECS + Docker Compose + GitHub Actions。本文档把「首次手动上线」列成清单——仓库里代码/CI 文件已全部就绪，服务器侧步骤需人工按清单执行。

---

## 1. 架构总览

```
                     ┌──────────────────────────────┐
   浏览器 / 微信小程序 │       阿里云 ECS（1 台）       │
        │            │                              │
        │ 80/443     │   nginx（网关，唯一对外入口）     │
        └───────────▶│   ├── /          → frontend    │
                     │   ├── /api/      → backend     │
                     │   ├── /health    → backend     │
                     │   └── /assets/   → frontend    │
                     │              │                 │
                     │   ┌──────────▼──────────┐      │
                     │   │  frontend (nginx)    │      │
                     │   │  + 静态 SPA 产物      │      │
                     │   └─────────────────────┘      │
                     │   ┌─────────────────────┐      │
                     │   │  backend (uvicorn)   │      │
                     │   │  entrypoint:         │      │
                     │   │  alembic upgrade head│      │
                     │   └───┬─────────┬────────┘      │
                     │   ┌────▼────┐ ┌──▼────┐        │
                     │   │ postgres│ │ redis │        │
                     │   └─────────┘ └───────┘        │
                     │   （可选）Dify CE：--profile dify│
                     └──────────────────────────────┘
```

- 所有端口仅绑定 `127.0.0.1`，对外只暴露 nginx。
- 与 crossborder-ai 同机共存时宿主机端口已偏移（见 docker-compose.yml）：nginx 80→8080、backend 8000→8001、postgres 5432→5433；容器内部端口与网关路由不变。
- 后端容器启动入口自动执行 `alembic upgrade head`（迁移是**唯一**的建表事实源，无 `create_all`）。
- 前端构建时 `VITE_API_BASE=""` → **同源部署**，浏览器直接打 `/api/*` 与 `/health`，由网关反代。
- Dify CE 走独立 `compose.dify.yml` + `profiles: ["dify"]`，**默认不启动**；启用时后端经 `DIFY_API_URL=http://api:5001/v1` 服务名直连。

---

## 2. 服务器布局

| 路径 | 内容 |
|---|---|
| `/opt/projecthub-ai/` | 仓库 clone（含 `docker-compose.yml`、`cicd-deploy.sh`） |
| `/opt/projecthub-ai/.env` | 生产配置（**不入库**，从 `.env.example` 复制后修改） |
| `/opt/projecthub-ai/nginx/ssl/` | 证书（certbot 生成后挂载，`cert.pem`/`key.pem`） |
| `/opt/projecthub-ai/nginx/www/` | certbot webroot 验证目录 |
| Docker volumes | `postgres_data`、`redis_data`（`docker volume ls` 查看） |

---

## 3. 前置条件

- 阿里云 ECS（Ubuntu 22.04+ / Debian 12+，建议 ≥2C4G）
- 安全组放行 8080（与 crossborder-ai 同机时网关入口；独立部署则放行 80，后续 443）
- 域名 A 记录指向 ECS 公网 IP（HTTPS 需要；纯 HTTP 可先跳过域名）
- GitHub 私有仓库（含本仓库代码）+ CI secrets

---

## 4. 首次手动上线清单（一次性，人工执行）

> 以下步骤**已从自动化脚本中剔除**，需首次部署时手动完成。完成后，日常更新走 GitHub Actions。

```bash
# ① 安装 Docker Engine + compose 插件（官方脚本）
curl -fsSL https://get.docker.com | bash
systemctl enable --now docker
apt-get update && apt-get install -y docker-compose-plugin
docker compose version   # 验证

# ② clone 私有仓库
git clone <你的私有仓库> /opt/projecthub-ai
cd /opt/projecthub-ai

# ③ 生成生产配置
cp .env.example .env
openssl rand -hex 32                      # 生成 JWT_SECRET
# 编辑 .env：POSTGRES_PASSWORD、JWT_SECRET 必改；
#   WECHAT_* 用不到可留空；DIFY_* 启用 Dify 时再填
nano .env

# ④ 首次启动（backend entrypoint 会自动跑 alembic 迁移）
docker compose up -d --build
docker compose ps                         # 5 服务均 Up/healthy
curl http://127.0.0.1:8080/health        # → {"status":"ok",...}
curl http://127.0.0.1:8080/api/projects  # → 401（未授权，符合预期）

# ⑤ HTTPS（证书 + 启用网关 HTTPS 块）
apt-get update && apt-get install -y certbot
#   a) 确认域名 A 记录已指向本机
#   b) 确保 nginx 以 HTTP 运行（默认即是）
#   c) 用 webroot 模式签证书（域名为你的域名）
mkdir -p nginx/www
certbot certonly --webroot -w nginx/www \
    -d your-domain.com \
    --non-interactive --agree-tos --email admin@your-domain.com
#   d) 拷贝证书到挂载目录
cp /etc/letsencrypt/live/your-domain.com/fullchain.pem nginx/ssl/cert.pem
cp /etc/letsencrypt/live/your-domain.com/privkey.pem  nginx/ssl/key.pem
#   e) 编辑 nginx/nginx.conf：启用底部 HTTPS server 块（把 server_name 换成你的域名），
#      注释/删除原 HTTP server，另加 80→443 的 301 跳转
nano nginx/nginx.conf
docker compose restart nginx
#   f) 配置自动续期（certbot renew 成功后重载 nginx）：
(crontab -l 2>/dev/null; echo "0 3 * * * certbot renew --quiet && cp /etc/letsencrypt/live/your-domain.com/fullchain.pem /opt/projecthub-ai/nginx/ssl/cert.pem && cp /etc/letsencrypt/live/your-domain.com/privkey.pem /opt/projecthub-ai/nginx/ssl/key.pem && docker compose -f /opt/projecthub-ai/docker-compose.yml restart nginx") | crontab -

# ⑥ 配置 GitHub Actions secrets（仓库 Settings → Secrets and variables → Actions）
#    PROJECTHUB_HOST      → ECS 公网 IP
#    PROJECTHUB_SSH_KEY   → root 的私钥（可新建专用密钥对，公钥写入服务器 ~/.ssh/authorized_keys）

# ⑦ 可选：启用 Dify CE（≥4G 内存再开）
docker compose -f docker-compose.yml -f compose.dify.yml --profile dify up -d
```

日常更新 = push main → CI 跑测试/构建 → deploy.yml SSH 到服务器执行 `bash /opt/projecthub-ai/cicd-deploy.sh`。

> `deploy.yml` 配了 `paths-ignore`（`**.md` / `docs/**` / `design-previews/**`）：**纯文档提交不会触发生产重建**。
> 只要提交里混有任何代码改动，部署照常执行。需要强制部署时用 GitHub 上的 `workflow_dispatch` 手动触发（不受路径过滤影响）。

---

## 5. Secrets 清单

| Secret（GitHub） / 变量（.env） | 说明 | 必填 |
|---|---|---|
| `PROJECTHUB_HOST` | ECS 公网 IP | GitHub 必填 |
| `PROJECTHUB_SSH_KEY` | root 私钥 | GitHub 必填 |
| `POSTGRES_PASSWORD` | PG 密码（强随机） | .env 必改 |
| `JWT_SECRET` | `openssl rand -hex 32`，**覆盖代码里的 dev 默认值** | .env 必改 |
| `DATABASE_URL` / `REDIS_URL` | 容器内主机名，模板已给，一般不用动 | — |
| `DIFY_API_URL` / `DIFY_API_KEY` | 启用 Dify 时填 | 可选 |
| `WECHAT_*` | 订阅消息，接入小程序时填 | 可选 |

---

## 6. 技术决策

| 决策 | 理由 |
|---|---|
| **alembic 入口迁移** | backend entrypoint `alembic upgrade head` 幂等；容器/CI 单点建表，`main.py` 无 `create_all` |
| **同源 `VITE_API_BASE=""`** | 前端构建时空串 → `/api` 同源；网关统一反代，无需 CORS 放行（生产仍默认 `*`，可收紧） |
| **Dify profile 门控** | Dify CE 全栈 ~4GB+ RAM，默认不启动；需要时 `--profile dify` 一键拉起 |
| **PG 用 postgres:16 非 pgvector** | 当前无向量列；Dify 自带 PG。日后需要向量检索 → 换镜像 + 一行迁移 |
| **仅核心 compose** | `cicd-deploy.sh` 只 `up` 核心服务，Dify 永不随部署自动启动 |

---

## 7. 安全加固

- 端口全绑 `127.0.0.1`；唯一对外入口 nginx。
- nginx 隐藏 `/docs`、`/openapi.json`、隐藏文件（`~ /\.` deny）。
- 安全头：`X-Frame-Options`、`X-Content-Type-Options`、`Referrer-Policy`、`Permissions-Policy`、HSTS（HTTPS 启用后）。
- `client_max_body_size 50M`；`/api/` 读超时 120s（AI 响应）。
- 每容器 `mem_limit` 兜底；`restart: unless-stopped`。
- `.env` 不入库（`.gitignore`）；`JWT_SECRET` 必须覆盖 dev 默认值。
- CORS `allow_origins=["*"]` 为 dev 默认——同源部署无跨域请求，可把 backend 配置改为 `["https://你的域名"]` 收紧。

---

## 8. 故障与回滚

| 症状 | 处置 |
|---|---|
| backend 一直 unhealthy | `docker compose logs --tail=50 backend` 看 alembic 报错（多为 .env 配置/DATABASE_URL 错误） |
| 迁移报错 | 手动 `docker compose exec backend alembic current` 对比 `alembic history`；新迁移出错时 `alembic downgrade -1` 后修迁移重跑 |
| 新版本有问题 | **回滚**：`cd /opt/projecthub-ai && git reset --hard <上一提交> && bash cicd-deploy.sh`（数据卷不动，仅代码回退） |
| 数据备份 | 定时 `docker compose exec -T postgres pg_dump -U ${POSTGRES_USER} ${POSTGRES_DB} > backup.sql`（建议 cron） |
| 磁盘/内存告警 | `docker system df`；`docker compose ps` 看单容器 mem_limit 命中情况 |
