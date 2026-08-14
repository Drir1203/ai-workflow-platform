export interface Project {
  id: string
  name: string
  description: string | null
  status: string
  color: string | null
  repo_url: string | null
  deploy_url: string | null
  local_path: string | null
  created_at: string
  updated_at: string
}

export interface Task {
  id: string
  project_id: string
  title: string
  description: string | null
  priority: string
  status: string
  due_date: string | null
  created_at: string
  updated_at: string
}

export interface Note {
  id: string
  project_id: string
  title: string
  content: string
  created_at: string
  updated_at: string
}

export interface User {
  id: string
  email: string
  name: string
  created_at: string
}

export interface AuthResponse {
  access_token: string
  token_type: string
  user: User
}

export interface ReminderResult {
  sent: number
  skipped: number
}

// ---------- 智能体（Phase 2） ----------

export interface AgentParam {
  name: string
  label: string
  type: string
  required: boolean
  default: unknown
  options: { value: string; label: string }[]
  placeholder: string
}

export interface AgentInfo {
  key: string
  name: string
  description: string
  param_schema: AgentParam[]
}

export interface AgentRun {
  id: string
  agent_key: string
  project_id: string | null
  status: string
  params: Record<string, unknown>
  output: string | null
  error: string | null
  started_at: string | null
  finished_at: string | null
  created_at: string
}
