# AI 工作流平台 · 竞品调研 + 实现方案（Wheel First + SDD）

> 项目：AI 工作流平台（临时代号 **ProjectHub AI**，可改名）
> 需求一句话：构建自己的 AI 工作流平台（Web + 微信小程序 + H5 + 原生 App 四端），用于管理项目（crossborder-ai、interview-coach）、处理日常工作与 AI 相关内容。
> 调研日期：2026-08-06

---

## 1. 需求解析

| 项 | 内容 |
|----|------|
| 目标用户 | 自己（单用户起步）→ 未来小团队 → 可能商业化 |
| 核心功能 | ①项目管理（多项目台账/看板/笔记）②日常任务管理 ③AI 对话助手 ④AI 智能体执行任务 ⑤知识库 RAG ⑥自动化工作流编排 |
| 形态 | Web + 微信小程序 + H5 + 原生 App（四端） |
| 技术诉求 | AI 深度接入（DeepSeek/Claude）、多端数据同步、预留多租户 |
| 约束 | 部署：阿里云 ECS + Docker + GitHub Actions（已有成熟管线）；复用 React / 原生小程序经验；单人开发、时间有限 |

---

## 2. 竞品概览（GitHub 调研 2026-08-06）

### 2.1 开源项目（按相关度排序）

| 名称 | Star | 语言 | License | 活跃 | 一句话定位 |
|------|------|------|---------|------|-----------|
| **n8n-io/n8n** | 199k | TypeScript | Sustainable Use（非开源，fair-code） | 极活跃 | 工作流自动化平台 + 原生 AI 节点，可视化编排最强 |
| **langgenius/dify** | 151k | TypeScript | Apache-2.0 修改版（附加限制） | 极活跃 | **对话+Agent+RAG+知识库+工作流编排 全栈**，自带多租户 |
| **langchain-ai/langchain** | 143k | Python | MIT | 极活跃 | Agent 工程框架（非平台） |
| **open-webui/open-webui** | 148k | Python | 自定义 | 极活跃 | 自托管 LLM 对话 UI |
| **infiniflow/ragflow** | 87k | Go/Python | **Apache-2.0** | 极活跃 | RAG 检索/深度文档解析最强 |
| **AppFlowy-IO/AppFlowy** | 75k | Dart/Flutter | AGPL-3.0 | 活跃 | Notion 类 AI 协作工作空间 |
| **Mintplex-Labs/anything-llm** | 64k | JavaScript | **MIT** ✅ | 极活跃 | 自托管 RAG+Agent+对话，完全可商用 |
| **lobehub/lobe-chat** | 81k | TypeScript | 自定义 | 极活跃 | 最好看的 AI 对话客户端（非平台） |
| **FlowiseAI/Flowise** | 55k | TypeScript | 自定义 | 活跃 | 可视化 LLM 流编排 |
| **labring/FastGPT** | 29k | TypeScript | Apache-2.0 + 商业条款 | 活跃 | 知识库 + 工作流 + Agent，国内生态好 |
| **hcengineering/platform (Huly)** | 27k | TypeScript | EPL-2.0 | 活跃 | 一体式项目管理（Linear/Jira/Slack/Notion 替代） |
| **coze-dev/coze-studio** | 21k | TypeScript | Apache-2.0 | 活跃 | 字节 Agent 平台开源子集 |
| **HKUDS/nanobot** | 47k | Python | MIT | 活跃 | 超轻量个人 AI Agent 框架 |
| **chatchat-space/Langchain-Chatchat** | 39k | Python | Apache-2.0 | 一般 | 本地模型 RAG + Agent 应用 |

### 2.2 SaaS 竞品（公开信息）

| 产品 | 定位 | 与我们的关系 |
|------|------|-------------|
| **Coze / 扣子**（字节） | AI Agent + 工作流 SaaS，有微信生态 | 功能对标对象；无自托管，受制于人 |
| **Dify Cloud** | Dify 托管版 | 若我们做平台 SaaS，直接竞争 |
| **Notion AI** | 工作空间 + AI 问答/写作 | 项目管理 + AI 的标杆，无国内小程序端 |
| **飞书 + AI 智能伙伴** | 企业 IM + 文档 + 多维表格 + AI | 国内企业工作台霸主；个人用太重 |

---

## 3. 功能对比矩阵

| 功能点 | Dify | n8n | RAGFlow | AnythingLLM | AppFlowy | Huly | **我们（目标）** |
|--------|------|-----|---------|-------------|----------|------|------------------|
| 项目管理/任务/看板 | ✗ 弱 | ✗ | ✗ | ✗ | ✅ | ✅✅ | ✅ 自研薄层 |
| AI 对话助手 | ✅✅ | 弱 | ✗ | ✅ | 弱 | 弱 | ✅ |
| 知识库 RAG | ✅ | ✗ | ✅✅ | ✅ | 弱 | ✗ | ✅ |
| AI 智能体执行任务 | ✅✅ | ✅(节点) | 部分 | ✅ | ✗ | ✗ | ✅ |
| 工作流可视化编排 | ✅ | ✅✅ | ✗ | ✗ | ✗ | ✗ | ✅（复用） |
| 多端（小程序/H5/App） | ✗ | ✗ | ✗ | 桌面/Web | 全端(Flutter) | Web | ✅ 自研 |
| 多租户 | ✅ 内置 | 企业版 | ✗ | ✗ | 云版 | 有 | ✅ 预留 |
| 商业化许可 | ⚠️ 受限 | ⚠️ 受限 | ✅ | ✅ | ❌ AGPL | ⚠️ | — |

---

## 4. 技术栈对比

| 维度 | Dify | n8n | AppFlowy | 建议（自研层） |
|------|------|-----|----------|--------------|
| 前端 | React+Next | Vue | Flutter | **React + Vite + shadcn/Tailwind**（复用 crossborder-ai 经验） |
| 后端 | Python FastAPI | TS/NestJS | Rust+TS | **Node (Fastify/Nest) 或 Python FastAPI**（已有两种经验） |
| 数据库 | PostgreSQL + pgvector | SQLite/Postgres | 自研 SQLite | **PostgreSQL + pgvector**（已有） |
| AI 接入 | 多模型 | 多模型 | 插件 | **DeepSeek / Claude / OpenAI 兼容适配**（已有） |
| 小程序 | ✗ | ✗ | Flutter→难 | **Taro（React 语法）→ 小程序/H5/App 一套代码** |
| 部署 | Docker | Docker | 各端 | **阿里云 ECS + Docker + GitHub Actions**（已有） |

---

## 5. 优缺点

### Dify（最佳复用候选）
- ✅ 四大 AI 能力全栈最全；自带多租户/工作区；API 完整（可 headless 对接）；社区最大
- ❌ License 是"修改版 Apache-2.0"：**禁止白标多租户 LLM 平台 SaaS**、禁止移除前端 LOGO；中文知识库检索不如 RAGFlow
- ⚠️ 合规路径：**单租户部署 / 作为内部后端引擎 / 构建自研编排层**（文档明确允许）；要商业化平台需联系官方商业授权

### n8n
- ✅ 工作流编排最成熟、节点生态最大；AI 节点内建
- ❌ Sustainable Use License：**禁止 resell "n8n-as-a-Service"**；Agent 能力弱于 Dify；无多租户

### RAGFlow
- ✅ Apache-2.0 干净；深度文档解析/检索最强
- ❌ 只解决 RAG 一层；对话/Agent/工作流要另配

### AnythingLLM
- ✅ **MIT，完全可商用**；RAG+Agent+对话全有；自托管简单
- ❌ 定位单实例桌面/自托管，多用户/工作流编排弱；UI 一般

### AppFlowy / Huly（借鉴数据模型）
- ✅ 项目/任务/看板模型成熟可借鉴
- ❌ AppFlowy 是 AGPL（SaaS 改了就传染）；Huly EPL + 附加条款，都**不能直接分叉商用**

### FastGPT / Coze Studio / LobeChat
- ✅ 各有亮点（FastGPT 国内生态好；Coze 体验佳；LobeChat UI 佳）
- ❌ FastGPT 商业条款限制对外 SaaS；Coze 开源版不完整；LobeChat 只是客户端

---

## 6. 复用决策（轮子决策）

| 功能模块 | 决策 | 依据 |
|----------|------|------|
| AI 对话/Agent/RAG/工作流编排 | **直接复用：自托管 Dify CE，headless API 对接** | 最全最成熟、有 API、社区大；作为内部引擎+自研前端属合规路径 |
| AI 引擎替换保险 | 适配层抽象 + 备选 **AnythingLLM(MIT)+RAGFlow(Apache)** | 若未来商业化踩 Dify 许可红线，可平替 |
| 项目管理/任务/看板 | **借鉴（Huly/AppFlowy 数据模型）+ 自研薄层** | 不做 Notion 级编辑器，轻量台账足够 |
| 用户/多租户/权限 | **自研**（先单租户，预留 tenant_id + workspace 隔离） | 商业化刚需，轻量实现 |
| Web 前端 | **直接复用** React + Vite + shadcn + Tailwind | 与 crossborder-ai 前端同栈 |
| 小程序 + H5 + 原生 App | **直接复用 Taro（React 语法）** | 一套代码 → 微信小程序/H5/React Native(App)，匹配 React 技能 |
| 部署/CI/CD | **直接复用** 阿里云 ECS + Docker + GitHub Actions + nginx | 已有成熟管线（interview-coach 已跑通） |
| 知识库向量检索 | 复用 PostgreSQL + pgvector（或 Dify 内置） | 已有 PG；避免再引 ES/Milvus |

---

## 7. 目标架构（外自研 · 内复用）

```
┌──────────────── 多端前端（自研，Taro 一套代码）────────────────┐
│  Web 桌面版(React)  │  微信小程序  │  H5  │  原生 App(RN)      │
└───────────────────────────┬──────────────────────────────────┘
                            │ HTTPS
┌───────────────────────────┴──────────────────────────────────┐
│  自研后端（Node 或 FastAPI）                                   │
│   ├─ 认证 + 多租户（tenant_id / workspace 隔离，预留商业化）     │
│   ├─ 业务层：项目 / 任务 / 笔记 / 项目集成（对接现有系统）        │
│   ├─ AI 适配层（抽象接口：chat / agent / rag / workflow）       │
│   └─ API 网关：REST + 未来 OpenAPI / webhooks                   │
├──────────────────────────────────────────────────────────────┤
│  AI 引擎：自托管 Dify CE（headless API）                        │
│   └─ 对话 / Agent / 知识库 RAG / 工作流编排（全部复用 Dify）      │
├──────────────────────────────────────────────────────────────┤
│  PostgreSQL + pgvector（业务数据 + 向量） · Redis（缓存/队列）    │
└──────────────────────────────────────────────────────────────┘
  部署：阿里云 ECS + Docker Compose + GitHub Actions + nginx
```

**关键设计：AI 适配层隔离。** 所有业务代码只面向 `IAiEngine` 接口（chat/agent/rag/workflow），底层可切换 Dify / AnythingLLM+RAGFlow / 直接 LLM。Dify 许可红线不影响自研层。

---

## 8. SDD 规格（能力点 + 需求场景）

> 依据 sdd-tdd 方法论：先定行为规格，用户确认后才进入 TDD 实现。

### Capability 1 · 项目工作台
- R1 用户可创建/管理多个项目（每个项目关联一个现有系统，如 crossborder-ai、interview-coach）
- R2 项目内有：概览页、任务列表、笔记、文档库、AI 问答入口
- R3 项目设公开/私有；未来可邀请成员
- 场景：登录后看到项目卡片 → 进入 crossborder-ai 项目 → 看最近巡检状态 → 问"上周巡检有什么异常"

### Capability 2 · 日常任务管理
- R4 任务 CRUD：标题/优先级/状态/截止时间/标签
- R5 看板视图 + 今日视图
- 场景：早上打开"今日"，把 5 个待办拖进完成列

### Capability 3 · AI 对话助手
- R6 全局对话 + 项目内对话（自动带项目上下文）
- R7 可切换模型（DeepSeek / Claude），记录 token 用量
- 场景：在 interview-coach 项目里问"押题逻辑是基于什么设计的？"

### Capability 4 · 知识库 RAG
- R8 上传文档（md/pdf/docx）自动切片入库
- R9 项目文档问答，回答附带引用来源
- R10 支持从现有项目 docs/ 目录自动采集（Agent 拉取）
- 场景：把 crossborder-ai 的 CLAUDE.md + 计划文档丢进知识库 → 问"部署流程是什么"

### Capability 5 · AI 智能体执行任务
- R11 预置 Agent：巡检报告生成、押题生成、竞品调研、周报生成
- R12 Agent 可调用工具：HTTP API、网页抓取、对接现有系统接口
- 场景：一键"生成本周项目进展周报" → Agent 读各项目数据 → 输出 Markdown

### Capability 6 · 工作流编排
- R13 可视化编排多步流程（复用 Dify 工作流，API 触发）
- R14 手动/定时触发，运行记录
- 场景：每周一 9 点自动"拉取各项目数据 → 汇总 → 生成周报 → 通知"

### Capability 7 · 多端一致
- R15 Web/小程序/H5/App 数据实时一致（同一后端）
- R16 微信小程序订阅消息推送（任务到期/流程完成）
- 场景：PC 上建任务 → 手机小程序收到到期提醒

### Capability 8 · 商业化预留
- R17 数据模型全部带 tenant_id（多租户隔离预留）
- R18 用量统计：API 调用数 / AI token / 存储量（为计费打基础）
- 场景：未来某天开启付费订阅时，能按租户计量出账单

---

## 9. 分阶段实施计划

### Phase 1 · MVP（约 3-4 周）— 跑通闭环
- [x] 项目骨架：Docker Compose（自研后端 + PG + Redis；Dify CE 以 `compose.dify.yml` + profile 门控接入，PG 先用 postgres:16 非 pgvector——无向量列，日后换镜像一行改动）
- [ ] 认证（先邮箱/密码单用户）+ 项目/任务/笔记 CRUD
- [ ] AI 适配层 + Dify headless 对接（对话 + 知识库 RAG）
- [ ] Web 端（React + Vite + shadcn）
- [ ] 小程序端（Taro，含订阅消息）
- [ ] 部署上线：阿里云 ECS + GitHub Actions（**代码与 CI/CD 文件已就绪**：ci.yml/deploy.yml/cicd-deploy.sh/DEPLOYMENT.md；剩余为服务器侧手动 TODO——装 Docker、建 .env、compose up、certbot HTTPS，见 DEPLOYMENT.md「首次部署清单」）

### Phase 2（约 3-4 周）— 智能体与工作流
- [ ] Agent 执行：预置 4 个 Agent + 工具调用
- [ ] 工作流编排（Dify workflows API）+ 定时触发
- [ ] 现有项目文档自动采集（对接 crossborder-ai / interview-coach docs）

### Phase 3（约 4 周）— 多端与商业化地基
- [ ] H5 端 + 原生 App（Taro/React Native 目标）
- [ ] 多租户隔离落地 + 用量统计
- [ ] 微信登录/支付预留

### Phase 4 · 商业化（按需）
- [ ] 计费订阅、团队邀请、开放 API

---

## 10. 风险与取舍

| 风险 | 等级 | 缓解 |
|------|------|------|
| **Dify 许可证**：未来商业化"多租户 AI 平台 SaaS"踩红线 | 高 | AI 适配层隔离；必要时平替 AnythingLLM(MIT)+RAGFlow(Apache)；Dify 仅作内部引擎属合规路径 |
| **范围蔓延**：四大 AI 能力 + 四端全做，单人拖垮 | 高 | MVP 只做"对话 + RAG + 轻任务"，Agent/工作流/App 放到 P2/P3 |
| **三端工作量**：Taro 虽省，RN 端调试成本仍高 | 中 | P3 再做 App；小程序+H5 优先 |
| **数据一致性**：自研后端 + Dify 两套库 | 中 | Dify 只存 AI 数据，业务数据全在 PG；通过 API 单向集成 |
| **对接现有系统**：crossborder-ai / interview-coach 数据结构各异 | 中 | 先做"项目卡片 + 文档采集"轻集成，深集成后置 |

---

## 11. 确认门禁

- [ ] 方案已完整呈现给用户（见上）
- [ ] 用户明确确认后才开始写代码
- [ ] 确认后按 sdd-tdd 流程：规格确认 → TDD（RED/GREEN/IMPROVE）→ code review → quality-gate

> 📋 **等待你的确认。** 可以调整的点：①AI 引擎选 Dify 还是 AnythingLLM+RAGFlow；②后端语言选 Node 还是 FastAPI；③MVP 范围（是否砍掉小程序先只做 Web）；④项目代号/目录名。

---

## 12. 确认记录（2026-08-06）

用户确认「按方案来」，主题先经 qiaomu-design 风格试衣间两轮选定：

| 项 | 决定 |
|----|------|
| 主题方向 | **A · 黑金旗舰（Obsidian）**，见 [DESIGN.md](../DESIGN.md)，唯一风格事实源 |
| AI 引擎 | Dify CE（headless API + AI 适配层隔离，平替备选 AnythingLLM+RAGFlow） |
| 后端语言 | Python FastAPI（与 Dify 同栈、AI 生态） |
| MVP 范围 | Phase 1 = Web + 小程序（Taro）首期同做 |
| 项目名 | ProjectHub AI / `ai-workflow-platform`（可改名） |
| 质量门禁 | SDD 规格已含（第 8 节）→ TDD（RED/GREEN/IMPROVE，≥80% 覆盖）→ code review → quality-gate |
