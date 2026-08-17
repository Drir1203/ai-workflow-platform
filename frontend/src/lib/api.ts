import type {
  AgentInfo,
  AgentParam,
  AgentRun,
  AuthResponse,
  CustomAgentRead,
  KnowledgeDocument,
  KnowledgeResponse,
  Note,
  Paginated,
  ParamTemplate,
  Project,
  ScanResult,
  Task,
  User,
  Workflow,
  WorkflowRun,
} from '../types'
import { BASE } from './mode'

const TOKEN_KEY = 'ph_token'
const USER_KEY = 'ph_user'

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY)
}

export function getSessionUser(): User | null {
  try {
    const raw = localStorage.getItem(USER_KEY)
    return raw ? (JSON.parse(raw) as User) : null
  } catch {
    return null
  }
}

export function setSession(r: AuthResponse) {
  localStorage.setItem(TOKEN_KEY, r.access_token)
  localStorage.setItem(USER_KEY, JSON.stringify(r.user))
}

export function clearSession() {
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(USER_KEY)
}

export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  const token = getToken()
  if (token) headers.Authorization = `Bearer ${token}`
  const res = await fetch(`${BASE}${path}`, {
    method,
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
  })
  if (res.status === 401) {
    clearSession()
    window.location.reload()
    throw new ApiError(401, '登录已过期')
  }
  if (!res.ok) {
    let detail = res.statusText
    try {
      const j = await res.json()
      detail = j.detail ?? JSON.stringify(j)
    } catch {
      /* keep default */
    }
    throw new ApiError(res.status, String(detail))
  }
  if (res.status === 204) return undefined as T
  return res.json() as Promise<T>
}

/** multipart 文件上传：浏览器自动带 boundary，不设 Content-Type。 */
async function upload<T>(path: string, file: File): Promise<T> {
  const form = new FormData()
  form.append('file', file)
  const headers: Record<string, string> = {}
  const token = getToken()
  if (token) headers.Authorization = `Bearer ${token}`
  const res = await fetch(`${BASE}${path}`, { method: 'POST', headers, body: form })
  if (res.status === 401) {
    clearSession()
    window.location.reload()
    throw new ApiError(401, '登录已过期')
  }
  if (!res.ok) {
    let detail = res.statusText
    try {
      const j = await res.json()
      detail = j.detail ?? JSON.stringify(j)
    } catch {
      /* keep default */
    }
    throw new ApiError(res.status, String(detail))
  }
  if (res.status === 204) return undefined as T
  return res.json() as Promise<T>
}

export const api = {
  login: (email: string, password: string) =>
    request<AuthResponse>('POST', '/api/auth/login', { email, password }),
  register: (email: string, password: string, name: string) =>
    request<AuthResponse>('POST', '/api/auth/register', { email, password, name }),
  listProjects: () => request<Project[]>('GET', '/api/projects'),
  createProject: (p: { name: string; description?: string; repo_url?: string; deploy_url?: string; local_path?: string }) =>
    request<Project>('POST', '/api/projects', p),
  deleteProject: (id: string) => request<void>('DELETE', `/api/projects/${id}`),
  listTasks: (projectId?: string) =>
    request<Task[]>('GET', `/api/tasks${projectId ? `?project_id=${projectId}` : ''}`),
  createTask: (t: { project_id: string; title: string; priority?: string; description?: string }) =>
    request<Task>('POST', '/api/tasks', t),
  updateTask: (id: string, patch: Partial<Task>) =>
    request<Task>('PATCH', `/api/tasks/${id}`, patch),
  deleteTask: (id: string) => request<void>('DELETE', `/api/tasks/${id}`),
  listNotes: (projectId?: string) =>
    request<Note[]>('GET', `/api/notes${projectId ? `?project_id=${projectId}` : ''}`),
  createNote: (n: { project_id: string; title: string; content?: string }) =>
    request<Note>('POST', '/api/notes', n),
  updateNote: (id: string, patch: Partial<Note>) =>
    request<Note>('PATCH', `/api/notes/${id}`, patch),
  deleteNote: (id: string) => request<void>('DELETE', `/api/notes/${id}`),
  chat: (query: string) => request<{ answer: string }>('POST', '/api/ai/chat', { query }),
  // ---------- Agent ----------
  listAgents: () => request<AgentInfo[]>('GET', '/api/agents'),
  runAgent: (agentKey: string, body: { params?: Record<string, unknown>; project_id?: string }) =>
    request<{ run_id: string; status: string }>('POST', `/api/agents/${agentKey}/run`, body),
  listAgentRuns: (opts?: { agent_key?: string; page?: number; page_size?: number }) => {
    const q = new URLSearchParams()
    if (opts?.agent_key) q.set('agent_key', opts.agent_key)
    q.set('page', String(opts?.page ?? 1))
    q.set('page_size', String(opts?.page_size ?? 20))
    return request<Paginated<AgentRun>>('GET', `/api/agents/runs?${q}`)
  },
  getAgentRun: (runId: string) => request<AgentRun>('GET', `/api/agents/runs/${runId}`),
  // ---------- 自定义 Agent（DB 持久化） ----------
  createAgent: (a: { name: string; description?: string | null; prompt: string; param_schema: AgentParam[] }) =>
    request<CustomAgentRead>('POST', '/api/agents', a),
  updateAgent: (key: string, patch: Partial<{ name: string; description?: string | null; prompt: string; param_schema: AgentParam[] }>) =>
    request<CustomAgentRead>('PATCH', `/api/agents/${key}`, patch),
  deleteAgent: (key: string) => request<void>('DELETE', `/api/agents/${key}`),
  // ---------- 参数预置模板 ----------
  listParamTemplates: (agentKey?: string) =>
    request<ParamTemplate[]>('GET', `/api/param-templates${agentKey ? `?agent_key=${agentKey}` : ''}`),
  createParamTemplate: (t: { name: string; agent_key: string; params: Record<string, unknown> }) =>
    request<ParamTemplate>('POST', '/api/param-templates', t),
  updateParamTemplate: (id: string, patch: Partial<{ name: string; params: Record<string, unknown> }>) =>
    request<ParamTemplate>('PATCH', `/api/param-templates/${id}`, patch),
  deleteParamTemplate: (id: string) => request<void>('DELETE', `/api/param-templates/${id}`),
  // ---------- 工作流 ----------
  listWorkflows: () => request<Workflow[]>('GET', '/api/workflows'),
  createWorkflow: (w: {
    name: string
    description?: string
    steps: { label: string; agent_key: string; params: Record<string, unknown> }[]
    schedule?: { cron?: string; interval_minutes?: number } | null
  }) => request<Workflow>('POST', '/api/workflows', w),
  updateWorkflow: (id: string, patch: Partial<Workflow>) =>
    request<Workflow>('PATCH', `/api/workflows/${id}`, patch),
  deleteWorkflow: (id: string) => request<void>('DELETE', `/api/workflows/${id}`),
  runWorkflow: (id: string) =>
    request<{ run_id: string; status: string }>('POST', `/api/workflows/${id}/run`),
  listWorkflowRuns: (opts?: { page?: number; page_size?: number }) => {
    const q = new URLSearchParams()
    q.set('page', String(opts?.page ?? 1))
    q.set('page_size', String(opts?.page_size ?? 20))
    return request<Paginated<WorkflowRun>>('GET', `/api/workflows/runs?${q}`)
  },
  getWorkflowRun: (runId: string) => request<WorkflowRun>('GET', `/api/workflows/runs/${runId}`),
  // ---------- 知识库 RAG ----------
  listDocuments: (projectId: string) =>
    request<KnowledgeDocument[]>('GET', `/api/projects/${projectId}/documents`),
  uploadDocument: (projectId: string, file: File) =>
    upload<KnowledgeDocument>(`/api/projects/${projectId}/documents`, file),
  deleteDocument: (projectId: string, documentId: string) =>
    request<void>('DELETE', `/api/projects/${projectId}/documents/${documentId}`),
  scanDocuments: (projectId: string) =>
    request<ScanResult>('POST', `/api/projects/${projectId}/documents/scan`),
  queryKnowledge: (projectId: string, query: string) =>
    request<KnowledgeResponse>('POST', `/api/projects/${projectId}/knowledge`, { query }),
}
