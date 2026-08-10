# ProjectHub AI - Frontend Dockerfile
# 多阶段构建：Node 构建 → Nginx 运行（仿 VeyaShip 模式）

# ════════════════════════════════════════════════════════════════
# 第一阶段：构建前端
# ════════════════════════════════════════════════════════════════
FROM node:20-alpine AS build

WORKDIR /app

# 先拷依赖文件，用缓存加速
COPY package.json package-lock.json* ./
# 有 package-lock.json 用 npm ci（更快更精确），否则用 npm install
RUN if [ -f package-lock.json ]; then npm ci; else npm install; fi

# 复制源码并构建。
# VITE_API_BASE 默认空串 → 同源部署：浏览器走 /api 与 /health，由网关 nginx 反代后端。
ARG VITE_API_BASE=""
ENV VITE_API_BASE="${VITE_API_BASE}"
COPY . .
RUN npm run build

# ════════════════════════════════════════════════════════════════
# 第二阶段：Nginx 运行（静态托管 + SPA fallback）
# ════════════════════════════════════════════════════════════════
FROM nginx:1.25-alpine AS production

COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
