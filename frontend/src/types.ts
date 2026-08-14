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

export type Mode = 'demo' | 'live'

// ---------- Agent / 工作流（Phase 2） ----------

export type AgentParamType = 'text' | 'textarea' | 'number' | 'select' | 'project_id'

export interface AgentParam {
  name: string
  label: string
  type: AgentParamType
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

export type RunStatus = 'pending' | 'running' | 'succeeded' | 'failed'

export interface AgentRun {
  id: string
  agent_key: string
  project_id: string | null
  status: RunStatus
  params: Record<string, unknown>
  output: string | null
  error: string | null
  started_at: string | null
  finished_at: string | null
  created_at: string
}

export interface WorkflowStep {
  label: string
  agent_key: string
  params: Record<string, unknown>
}

export interface Schedule {
  cron: string | null
  interval_minutes: number | null
}

export interface Workflow {
  id: string
  user_id: string
  name: string
  description: string | null
  steps: WorkflowStep[]
  schedule: Schedule | null
  enabled: boolean
  created_at: string
  updated_at: string
}

export interface WorkflowRunResult {
  label: string
  agent_key: string
  output: string
}

export interface WorkflowRun {
  id: string
  workflow_id: string
  status: RunStatus
  results: WorkflowRunResult[] | null
  error: string | null
  triggered_by: 'manual' | 'scheduled'
  started_at: string | null
  finished_at: string | null
  created_at: string
}

export interface Paginated<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}

// ---------- 知识库 RAG（Capability 4） ----------

export interface KnowledgeDocument {
  id: string
  project_id: string
  name: string
  source: string // upload | scan
  content_type: string // md | txt | pdf | docx
  status: string // ready | processing | error
  error: string | null
  source_path: string | null
  created_at: string
}

export interface KnowledgeSource {
  document_id: string
  document_name: string
  seq: number
  content: string
  matched: string[]
}

export interface KnowledgeResponse {
  answer: string
  sources: KnowledgeSource[]
}

export interface ScanResult {
  imported: number
  skipped: string[]
}
