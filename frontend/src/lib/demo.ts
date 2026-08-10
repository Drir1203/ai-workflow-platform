import type { Note, Project, Task } from '../types'

const iso = (daysAgo: number, h = 10) => {
  const d = new Date()
  d.setDate(d.getDate() - daysAgo)
  d.setHours(h, (24 - (daysAgo % 24) * 3) % 60, 0, 0)
  return d.toISOString()
}

let projects: Project[] = [
  {
    id: 'p-1', name: 'CrossBorder AI', status: 'active',
    description: '1688 商品数据源 · 整店巡检闭环 · 环境变量巡检',
    color: '#D9A441', repo_url: 'https://github.com/Drir1203/crossborder-ai',
    deploy_url: null, local_path: null, created_at: iso(38), updated_at: iso(0, 9),
  },
  {
    id: 'p-2', name: 'i面试 · AI 教练', status: 'active',
    description: 'AI 面试教练 · 押题 · 闭环 · 成长报告 · 简历解析',
    color: '#E8C078', repo_url: 'https://github.com/Drir1203/interview-coach',
    deploy_url: null, local_path: null, created_at: iso(30), updated_at: iso(1),
  },
  {
    id: 'p-3', name: 'ProjectHub AI 平台', status: 'planning',
    description: '工作流平台 · 黑金旗舰主题 · Web/小程序/App',
    color: '#A9762B', repo_url: 'https://github.com/Drir1203/ai-workflow-platform',
    deploy_url: 'https://projecthub.example.app', local_path: null,
    created_at: iso(2), updated_at: iso(0, 8),
  },
  {
    id: 'p-4', name: '日常工作', status: 'active',
    description: '周报、待办、灵感速记、AI 内容整理',
    color: '#8FA8C0', repo_url: null, deploy_url: null, local_path: null,
    created_at: iso(60), updated_at: iso(0, 7),
  },
]

let tasks: Task[] = [
  { id: 't-1', project_id: 'p-1', title: '1688 数据源整店巡检', description: '跑通 5.0 巡检闭环并核对结果', priority: 'high', status: 'in_progress', due_date: '2026-08-06', created_at: iso(3), updated_at: iso(0) },
  { id: 't-2', project_id: 'p-1', title: '环境变量巡检清单', description: 'GBK / PG schema 对齐', priority: 'medium', status: 'done', due_date: null, created_at: iso(5), updated_at: iso(2) },
  { id: 't-3', project_id: 'p-1', title: 'Onebound 接口开通需求', description: '整理需求文档', priority: 'low', status: 'todo', due_date: '2026-08-10', created_at: iso(1), updated_at: iso(1) },
  { id: 't-4', project_id: 'p-2', title: '移动端改为微信小程序 v3', description: '含订阅消息待办', priority: 'high', status: 'in_progress', due_date: '2026-08-07', created_at: iso(2), updated_at: iso(0, 9) },
  { id: 't-5', project_id: 'p-2', title: '成长报告导出', description: '', priority: 'medium', status: 'todo', due_date: null, created_at: iso(2), updated_at: iso(1) },
  { id: 't-6', project_id: 'p-3', title: 'Web 前端 · 黑金主题 Demo', description: 'Vite + React + Tailwind', priority: 'high', status: 'in_progress', due_date: '2026-08-06', created_at: iso(0), updated_at: iso(0) },
  { id: 't-7', project_id: 'p-3', title: '后端 23/23 测试全绿', description: 'FastAPI + SQLAlchemy async', priority: 'medium', status: 'done', due_date: null, created_at: iso(1), updated_at: iso(0) },
  { id: 't-8', project_id: 'p-4', title: '本周周报', description: '', priority: 'medium', status: 'todo', due_date: '2026-08-08', created_at: iso(1), updated_at: iso(0) },
]

let notes: Note[] = [
  { id: 'n-1', project_id: 'p-1', title: '巡检要点', content: '1688 数据源巡检的闭环步骤：爬取 → 校验 → 比对 → 上报，5.0 已全流程跑通。', created_at: iso(4), updated_at: iso(2) },
  { id: 'n-2', project_id: 'p-1', title: '环境变量陷阱', content: '.env 位置、PG schema 不匹配、GBK 下 emoji 会崩溃 —— 三处易踩坑都记录在案。', created_at: iso(3), updated_at: iso(1) },
  { id: 'n-3', project_id: 'p-2', title: '产品形态备忘', content: '移动端现状为微信小程序 v3，后续 H5 与原生 App 共用 Taro 一套代码。', created_at: iso(2), updated_at: iso(0) },
  { id: 'n-4', project_id: 'p-3', title: '主题决策', content: '黑金旗舰（Obsidian）已确认，DESIGN.md 为唯一风格事实源，主色香槟金 #D9A441。', created_at: iso(0), updated_at: iso(0) },
  { id: 'n-5', project_id: 'p-4', title: '本周灵感', content: '把日常工作里的 AI 内容整理也接进知识库 RAG，减少重复查询。', created_at: iso(1), updated_at: iso(1) },
]

const delay = (ms = 180) => new Promise((r) => setTimeout(r, ms))
let nid = 100
let tid = 100

function demoReply(q: string): string {
  const s = q.toLowerCase()
  if (s.includes('项目') || s.includes('project')) {
    return '工作区现有 4 个活跃项目。CrossBorder AI 的整店巡检闭环推进中（68.5%），i面试 教练移动端已切换为小程序 v3。需要我汇总某个项目的任务进度吗？'
  }
  if (s.includes('部署') || s.includes('dify') || s.includes('ai')) {
    return 'AI 引擎通过适配层对接 Dify CE（headless Service API）。未配置 DIFY_API_KEY 时返回 503；生产建议把密钥注入环境变量，测试用 FakeEngine 注入。'
  }
  if (s.includes('任务') || s.includes('待办')) {
    return '本周已完成 27 项任务，进行中 9 项，其中 3 项今日截止。建议优先处理 priority = high 的两项巡检任务。'
  }
  return '我已接入工作区数据。可以问我项目进度、任务待办、部署状态或任意 AI 相关问题——生产环境由 Dify 引擎回答，当前为演示数据。'
}

export const demoApi = {
  async listProjects(): Promise<Project[]> {
    await delay()
    return [...projects]
  },
  async createProject(p: { name: string; description?: string; repo_url?: string; deploy_url?: string; local_path?: string }): Promise<Project> {
    await delay()
    const now = new Date().toISOString()
    const proj: Project = {
      id: `p-${++tid}`, name: p.name, description: p.description ?? null,
      status: 'active', color: '#D9A441',
      repo_url: p.repo_url ?? null, deploy_url: p.deploy_url ?? null, local_path: p.local_path ?? null,
      created_at: now, updated_at: now,
    }
    projects = [proj, ...projects]
    return proj
  },
  async deleteProject(id: string): Promise<void> {
    await delay()
    projects = projects.filter((p) => p.id !== id)
    tasks = tasks.filter((t) => t.project_id !== id)
    notes = notes.filter((n) => n.project_id !== id)
  },
  async listTasks(projectId?: string): Promise<Task[]> {
    await delay()
    const list = projectId ? tasks.filter((t) => t.project_id === projectId) : tasks
    return [...list]
  },
  async createTask(t: { project_id: string; title: string; priority?: string; description?: string }): Promise<Task> {
    await delay()
    const now = new Date().toISOString()
    const task: Task = {
      id: `t-${++tid}`, project_id: t.project_id, title: t.title,
      description: t.description ?? null, priority: t.priority ?? 'medium',
      status: 'todo', due_date: null, created_at: now, updated_at: now,
    }
    tasks = [task, ...tasks]
    return task
  },
  async updateTask(id: string, patch: Partial<Task>): Promise<Task> {
    await delay()
    tasks = tasks.map((t) => (t.id === id ? { ...t, ...patch, updated_at: new Date().toISOString() } : t))
    return tasks.find((t) => t.id === id)!
  },
  async deleteTask(id: string): Promise<void> {
    await delay()
    tasks = tasks.filter((t) => t.id !== id)
  },
  async listNotes(projectId?: string): Promise<Note[]> {
    await delay()
    const list = projectId ? notes.filter((n) => n.project_id === projectId) : notes
    return [...list]
  },
  async createNote(n: { project_id: string; title: string; content?: string }): Promise<Note> {
    await delay()
    const now = new Date().toISOString()
    const note: Note = {
      id: `n-${++nid}`, project_id: n.project_id, title: n.title,
      content: n.content ?? '', created_at: now, updated_at: now,
    }
    notes = [note, ...notes]
    return note
  },
  async updateNote(id: string, patch: Partial<Note>): Promise<Note> {
    await delay()
    notes = notes.map((n) => (n.id === id ? { ...n, ...patch, updated_at: new Date().toISOString() } : n))
    return notes.find((n) => n.id === id)!
  },
  async deleteNote(id: string): Promise<void> {
    await delay()
    notes = notes.filter((n) => n.id !== id)
  },
  async chat(query: string): Promise<{ answer: string }> {
    await delay(420)
    return { answer: demoReply(query) }
  },
}
