#!/usr/bin/env bash
# ════════════════════════════════════════════════════════════════
# AI智序 - 服务器首次部署脚本（半自动：装 Docker + 生成 .env + 部署）
# ════════════════════════════════════════════════════════════════
# 用法（目标服务器 root 下，一次性）：
#
#   ① 让服务器能拉私有仓库（2 分钟，只做一次）：
#        ssh-keygen -t ed25519 -N '' -f ~/.ssh/id_ed25519
#        cat ~/.ssh/id_ed25519.pub     # 复制整段，粘贴到 GitHub
#                                      # 仓库 Settings → Deploy keys → Add（勾 Allow write access）
#        ssh-keyscan github.com >> ~/.ssh/known_hosts
#
#   ② clone 并一键部署：
#        git clone git@github.com:Drir1203/ai-workflow-platform.git /opt/projecthub-ai
#        cd /opt/projecthub-ai && sudo bash setup-server.sh
#
# 可选环境变量（全部不传也能跑，AI 已切到 OpenAI 兼容但需你事后补 key）：
#   AI_PROVIDER=openai_compatible|dify   （默认 openai_compatible，免 Dify）
#   OPENAI_COMPATIBLE_API_KEY=xxx        （DeepSeek/通义 key；openai_compatible 模式建议填）
#   POSTGRES_PASSWORD=xxx                （不传则自动随机生成）
#
# 幂等：Docker 已装 / .env 已存在 / 仓库已 clone 均自动跳过，可安全重跑。
# ════════════════════════════════════════════════════════════════

set -euo pipefail

PROJECT_DIR="/opt/projecthub-ai"
AI_PROVIDER="${AI_PROVIDER:-openai_compatible}"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
print_step() { echo -e "\n${GREEN}━━━ $1 ━━━${NC}"; }
print_info() { echo -e "  ${YELLOW}→${NC} $1"; }
print_ok()   { echo -e "  ${GREEN}✓${NC} $1"; }
print_err()  { echo -e "  ${RED}✗${NC} $1"; }

# ── ① 前置检查 ──────────────────────────────────────────────────
print_step "① 前置检查"
if [ "$(id -u)" -ne 0 ]; then
    print_err "请用 root 运行（sudo bash setup-server.sh）"; exit 1
fi
if [ ! -d "$PROJECT_DIR/.git" ]; then
    print_err "$PROJECT_DIR 不存在或不是 git 仓库。"
    print_err "请先配好 GitHub Deploy key 后手动 clone："
    print_err "  git clone git@github.com:Drir1203/ai-workflow-platform.git $PROJECT_DIR"
    exit 1
fi
print_ok "仓库就绪：$PROJECT_DIR"

# ── ② 安装 Docker + compose 插件（幂等）─────────────────────────
print_step "② 安装 Docker + compose 插件"
if ! command -v docker &> /dev/null; then
    print_info "安装 Docker Engine（官方脚本）..."
    curl -fsSL https://get.docker.com | bash
    systemctl enable --now docker
else
    print_ok "Docker 已安装：$(docker --version)"
fi
if ! docker compose version &> /dev/null; then
    print_info "安装 docker compose 插件..."
    apt-get update -y && apt-get install -y docker-compose-plugin
else
    print_ok "Compose：$(docker compose version | head -1)"
fi

# ── ③ 拉取最新代码 ──────────────────────────────────────────────
print_step "③ 拉取最新代码"
cd "$PROJECT_DIR"
git fetch origin main && git reset --hard origin/main
print_ok "代码已更新到 $(git rev-parse --short HEAD)"

# ── ④ 生成 .env（已存在则跳过，避免覆盖）────────────────────────
print_step "④ 生成生产配置 .env"
if [ -f "$PROJECT_DIR/.env" ]; then
    print_info ".env 已存在，跳过生成（如需重置：rm .env 后重跑）"
else
    cp .env.example .env
    PG_PW="${POSTGRES_PASSWORD:-$(openssl rand -hex 16)}"
    JWT_SECRET="$(openssl rand -hex 32)"
    sed -i "s/POSTGRES_PASSWORD=change-me/POSTGRES_PASSWORD=$PG_PW/" .env
    sed -i "s|postgresql+asyncpg://projecthub:change-me@postgres:5432/projecthub|postgresql+asyncpg://projecthub:$PG_PW@postgres:5432/projecthub|" .env
    sed -i "s|JWT_SECRET=change-me-with-openssl-rand-hex-32|JWT_SECRET=$JWT_SECRET|" .env
    sed -i "s/^AI_PROVIDER=dify/AI_PROVIDER=$AI_PROVIDER/" .env
    if [ -n "${OPENAI_COMPATIBLE_API_KEY:-}" ]; then
        sed -i "s/^OPENAI_COMPATIBLE_API_KEY=$/OPENAI_COMPATIBLE_API_KEY=$OPENAI_COMPATIBLE_API_KEY/" .env
    fi
    print_ok "已生成 .env（POSTGRES_PASSWORD / JWT_SECRET 已自动随机化）"
    if [ "$AI_PROVIDER" = "openai_compatible" ] && [ -z "${OPENAI_COMPATIBLE_API_KEY:-}" ]; then
        print_err "提醒：AI_PROVIDER=openai_compatible 但 OPENAI_COMPATIBLE_API_KEY 为空。"
        print_err "      请 nano .env 填入你的 DeepSeek/通义 key 后再跑第⑤步。"
    fi
fi

# ── ⑤ 构建并部署（entrypoint 自动跑 alembic 迁移）───────────────
print_step "⑤ 构建并部署"
bash "$PROJECT_DIR/cicd-deploy.sh"

print_step "✅ 部署完成"
print_info "验证：curl http://127.0.0.1:8080/health"
print_info "浏览器打开 http://服务器IP:8080/（HTTP 有'不安全'提示，属预期）"
