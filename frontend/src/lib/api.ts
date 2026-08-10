import type { AuthResponse, Note, Project, Task, User } from '../types'
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
}
