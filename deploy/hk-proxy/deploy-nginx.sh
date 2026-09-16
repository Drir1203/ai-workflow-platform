#!/usr/bin/env bash
# ============================================================
# 雅秩（projecthub-ai）—— 香港反向代理上线脚本（nginx + certbot）
#
# 架构：
#   浏览器 → https://<域名>（香港服务器，certbot 证书）
#          → http://47.116.138.61:8080（阿里云容器 nginx）
#          → frontend / backend 容器
#
# ── 与 crossborder-ai（veyaship.com）反代的关键差异 ──
#   veyaship 上游是 443，靠「IP 建连 + 不发 SNI（proxy_ssl_server_name off）」
#   让阿里云在 TLS 层看不见域名，从而绕过备案拦截。
#
#   本项目上游是 8080 **明文 HTTP**，没有 SNI 层可绕。
#   实测（2026-09）：
#     Host: 47.116.138.61:8080      → 200
#     Host: veyaship.com            → 403 Non-compliance ICP Filing
#     Host: <任意未记录域名>         → 200（阿里云是黑名单式拦截，只拦已记录域名）
#   即：阿里云在 8080 上按 Host 头拦截，且新域名在「被扫到并记录」之前能过 ——
#   这是个不稳定状态，随时可能二次演示当天变 403。
#
#   因此这里把 Host 头改写成 IP，让阿里云无从按域名判定，换取确定性。
#   后端不依赖 Host 头（无 request.base_url、无 OAuth 回调；
#   微信通知走小程序内部路径 pages/project/index，非 HTTP URL），
#   故改写 Host 无副作用。真实域名经 X-Forwarded-Host 透传备用。
#
# ── 前置条件（缺一不可）──
#   1. DNS：<域名> 与 www.<域名> A 记录已指向本机（香港服务器公网 IP）
#   2. 阿里云安全组：8080 入方向放行本机 IP
#   3. 本机 80/443 未被占用（或已有 nginx，脚本会 reload 而非 restart）
# 执行方式（在本机执行）：
#   DOMAIN=your-domain.com bash deploy-nginx.sh
# 幂等：可重复执行，覆盖同名 vhost 与缓存配置，不影响其他站点
# ============================================================
set -e

DOMAIN="${DOMAIN:?用法: DOMAIN=your-domain.com bash deploy-nginx.sh}"

UPSTREAM_HOST=47.116.138.61
UPSTREAM_PORT=8080
UPSTREAM_ADDR="$UPSTREAM_HOST:$UPSTREAM_PORT"

SRV=/etc/nginx/sites-available/"$DOMAIN"
ENL=/etc/nginx/sites-enabled/"$DOMAIN"
# 缓存区名只能用字母数字下划线，故把域名里的点换成下划线
ZONE=$(echo "$DOMAIN" | tr '.' '_')
CACHE_CONF=/etc/nginx/conf.d/"$ZONE"-cache.conf
CACHE_DIR=/var/cache/nginx/"$ZONE"

echo "==> 阶段0：准备静态资源缓存目录"
# proxy_cache_path 只能声明在 http 上下文，站点文件里放不下，故单独走 conf.d
sudo mkdir -p "$CACHE_DIR"
sudo chown -R www-data:www-data /var/cache/nginx

echo "==> 阶段1：仅 80 端口（供 ACME 验证）"
sudo mkdir -p /var/www/html
sudo tee "$SRV" >/dev/null <<NGINX
server {
    listen 80;
    server_name $DOMAIN www.$DOMAIN;
    location /.well-known/acme-challenge/ { root /var/www/html; }
    location / { return 301 https://\$host\$request_uri; }
}
NGINX
sudo ln -sf "$SRV" "$ENL"
sudo nginx -t && sudo systemctl reload nginx
echo "phase1 ok"

echo "==> 阶段2：certbot 签证书（HTTP-01）"
sudo certbot certonly --webroot -w /var/www/html \
  -d "$DOMAIN" -d www."$DOMAIN" \
  --non-interactive --agree-tos --email admin@"$DOMAIN" --no-eff-email
echo "cert ok"

echo "==> 阶段3：缓存区声明"
sudo tee "$CACHE_CONF" >/dev/null <<NGINX
# $DOMAIN 静态资源边缘缓存
# 前端产物文件名带内容 hash 且响应头 immutable，可安全长缓存；
# 香港→上海 RTT 约 165ms，静态产物命中缓存后不必回源。
proxy_cache_path $CACHE_DIR levels=1:2
                 keys_zone=${ZONE}_static:10m
                 max_size=1g inactive=30d use_temp_path=off;
NGINX

echo "==> 阶段4：完整反代配置（80 + 443）"
sudo tee "$SRV" >/dev/null <<NGINX
# $DOMAIN —— 香港反代到阿里云 8080
#
# 关键点：
#   1) proxy_pass 写 IP:8080 且为 http → 上游无 SNI，且 Host 头另行改写（见 2）
#   2) Host 头写 IP     → 阿里云按 Host 拦未备案域名，写 IP 可规避（详见脚本头注释）
#   3) proxy_buffering off → copilot / writing 是 SSE 流式，开缓冲会导致前端收不到增量。
#                            后端已发 X-Accel-Buffering: no，这里再关一层兜底。
#   4) gzip_proxied any → 系统 nginx.conf 默认 gzip_types/gzip_proxied 是注释掉的，
#                          不加这行反代响应一律不压缩，等于前端产物裸传。
#   5) /assets/ 走边缘缓存 → 跨境 RTT 高，静态产物复用后不回源。
#
# 连接池：keepalive 复用长连接，避免每请求重新握手（跨境 0.3~0.8s 且抖动大）。
upstream ${ZONE}_origin {
    server $UPSTREAM_ADDR;
    keepalive 32;
    keepalive_timeout 60s;
}

server {
    listen 443 ssl http2;
    server_name $DOMAIN www.$DOMAIN;

    ssl_certificate     /etc/letsencrypt/live/$DOMAIN/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/$DOMAIN/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    # 跨境链路 RTT 高，复用会话可省掉重复的完整握手
    ssl_session_cache   shared:${ZONE}_ssl:10m;
    ssl_session_timeout 1d;
    ssl_session_tickets on;

    client_max_body_size 50m;   # 与容器 nginx 的 client_max_body_size 一致

    gzip on;
    gzip_proxied any;           # 关键：不加这行，反代响应一律不压缩
    gzip_comp_level 5;
    gzip_min_length 1024;
    gzip_vary on;
    gzip_types text/plain text/css application/javascript application/json
               application/xml image/svg+xml;

    # 带 hash 的构建产物：边缘缓存，命中后不回源
    location /assets/ {
        proxy_pass http://${ZONE}_origin;
        proxy_http_version 1.1;
        proxy_set_header Connection        "";
        proxy_set_header Host              $UPSTREAM_ADDR;
        proxy_set_header X-Forwarded-Host  \$host;
        proxy_set_header X-Forwarded-Proto \$scheme;

        proxy_cache            ${ZONE}_static;
        proxy_cache_valid      200 30d;
        proxy_cache_use_stale  error timeout updating http_500 http_502 http_503 http_504;
        proxy_cache_lock       on;
        add_header X-Cache-Status \$upstream_cache_status always;
    }

    location / {
        proxy_pass http://${ZONE}_origin;
        proxy_http_version 1.1;
        # 清空 Connection 是启用 upstream keepalive 的必要条件
        proxy_set_header Connection        "";

        # Host 写成 IP：让阿里云无法按域名判定备案状态（本项目绕不开的核心点）
        proxy_set_header Host              $UPSTREAM_ADDR;
        # 真实域名经 X-Forwarded-Host 透传，便于后端日后需要时取用
        proxy_set_header X-Forwarded-Host  \$host;
        proxy_set_header X-Real-IP         \$remote_addr;
        # 用 \$remote_addr 而非 \$proxy_add_x_forwarded_for：避免客户端伪造 XFF 后
        # 真实 IP 被挤到第二位。注意后端限流取 request.client.host（TCP 对端），
        # uvicorn 未开 --proxy-headers，故此处 XFF 目前不会被后端读取。
        proxy_set_header X-Forwarded-For   \$remote_addr;
        proxy_set_header X-Forwarded-Proto \$scheme;

        # SSE（copilot / writing 流式输出）必须关缓冲
        proxy_buffering off;
        proxy_cache     off;

        # AI 请求较慢：容器 nginx 侧是 120s，这里放宽到 300s 覆盖跨境往返
        proxy_read_timeout 300s;
        proxy_send_timeout 300s;
    }
}

server {
    listen 80;
    server_name $DOMAIN www.$DOMAIN;
    location /.well-known/acme-challenge/ { root /var/www/html; }
    location / { return 301 https://\$host\$request_uri; }
}
NGINX
sudo nginx -t && sudo systemctl reload nginx
echo "NGINX_DONE"
echo
echo "验证："
echo "  curl -I https://$DOMAIN/health          # 期望 200 {\"status\":\"ok\",...}"
echo "  curl -I http://$UPSTREAM_ADDR/health    # 本机回源基线，期望 200"
