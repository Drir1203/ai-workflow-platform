import Taro from '@tarojs/taro'
import type {
  AgentInfo,
  AgentRun,
  AuthResponse,
  Note,
  Project,
  ReminderResult,
  Task,
  User,
} from '../types'
import { BASE } from './config'

const TOKEN_KEY = 'ph_token'
const USER_KEY = 'ph_user'

export function getToken(): string {
  return Taro.getStorageSync(TOKEN_KEY) || ''
}

export function getSessionUser(): User | null {
  try {
    const raw = Taro.getStorageSync(USER_KEY)
    return raw ? (JSON.parse(raw) as User) : null
  } catch {
    return null
  }
}

export function setSession(r: AuthResponse): void {
  Taro.setStorageSync(TOKEN_KEY, r.access_token)
  Taro.setStorageSync(USER_KEY, JSON.stringify(r.user))
}

export function clearSession(): void {
  Taro.removeStorageSync(TOKEN_KEY)
  Taro.removeStorageSync(USER_KEY)
}

export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  const token = getToken()
  const header: Record<string, string> = { 'Content-Type': 'application/json' }
  if (token) header.Authorization = `Bearer ${token}`
  let res
  try {
    res = await Taro.request({
      url: `${BASE}${path}`,
      method: method as any,
      data: body === undefined ? undefined : JSON.stringify(body),
      header,
      timeout: 20000,
    })
  } catch {
    throw new ApiError(0, '网络异常，请确认后端已启动')
  }
  if (res.statusCode === 401) {
    clearSession()
    Taro.reLaunch({ url: '/pages/login/index' })
    throw new ApiError(401, '登录已过期')
  }
  if (res.statusCode < 200 || res.statusCode >= 300) {
    let detail = `请求失败 (${res.statusCode})`
    const data = res.data as { detail?: unknown } | undefined
    if (data && data.detail) detail = String(data.detail)
    throw new ApiError(res.statusCode, detail)
  }
  return res.data as T
}

export const api = {
  login: (email: string, password: string) =>
    request<AuthResponse>('POST', '/api/auth/login', { email, password }),
  register: (email: string, password: string, name: string) =>
    request<AuthResponse>('POST', '/api/auth/register', { email, password, name }),

  listProjects: () => request<Project[]>('GET', '/api/projects'),
  createProject: (p: { name: string; description?: string }) =>
    request<Project>('POST', '/api/projects', p),
  deleteProject: (id: string) => request<void>('DELETE', `/api/projects/${id}`),

  listTasks: (projectId?: string) =>
    request<Task[]>('GET', `/api/tasks${projectId ? `?project_id=${projectId}` : ''}`),
  createTask: (t: { project_id: string; title: string; priority?: string; due_date?: string | null }) =>
    request<Task>('POST', '/api/tasks', t),
  updateTask: (id: string, patch: Partial<Task>) =>
    request<Task>('PATCH', `/api/tasks/${id}`, patch),
  deleteTask: (id: string) => request<void>('DELETE', `/api/tasks/${id}`),

  listNotes: (projectId?: string) =>
    request<Note[]>('GET', `/api/notes${projectId ? `?project_id=${projectId}` : ''}`),
  createNote: (n: { project_id: string; title: string; content?: string }) =>
    request<Note>('POST', '/api/notes', n),
  deleteNote: (id: string) => request<void>('DELETE', `/api/notes/${id}`),

  chat: (query: string) => request<{ answer: string }>('POST', '/api/ai/chat', { query }),

  // 智能体
  listAgents: () => request<AgentInfo[]>('GET', '/api/agents'),
  runAgent: (agentKey: string, body: { params?: Record<string, unknown>; project_id?: string }) =>
    request<{ run_id: string; status: string }>('POST', `/api/agents/${agentKey}/run`, body),
  getAgentRun: (runId: string) => request<AgentRun>('GET', `/api/agents/runs/${runId}`),

  wechatSubscribe: (code: string, task_id: string, template_id?: string) =>
    request<{ task_id: string; status: string }>('POST', '/api/wechat/subscribe', {
      code,
      task_id,
      template_id,
    }),
  sendReminders: () => request<ReminderResult>('POST', '/api/wechat/reminders/send', {}),
}
