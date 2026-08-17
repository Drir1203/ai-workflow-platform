import { useCallback, useEffect, useMemo, useState } from 'react'
import { Badge } from '../components/ui/badge'
import { Button } from '../components/ui/button'
import { Card } from '../components/ui/card'
import { Dialog } from '../components/ui/dialog'
import { Empty } from '../components/ui/empty'
import { Input, Textarea } from '../components/ui/input'
import type { DataLayer } from '../lib/view'
import type { AgentInfo, AgentParam, AgentParamType, AgentRun, ParamTemplate, Project, RunStatus } from '../types'

function statusTone(status: RunStatus) {
  return status === 'succeeded' ? 'success' : status === 'failed' ? 'error' : 'info'
}

const statusLabel: Record<RunStatus, string> = {
  pending: '排队中',
  running: '执行中',
  succeeded: '成功',
  failed: '失败',
}

// 新建/编辑自定义 Agent 时的参数字段草稿（default 用字符串编辑，提交时按 type 转换）
interface AgentDraftParam {
  name: string
  label: string
  type: AgentParamType
  required: boolean
  default: string
}

const emptyParam = (): AgentDraftParam => ({ name: '', label: '', type: 'text', required: false, default: '' })

// 自定义 Agent 可选的参数类型：不含 select（选择项无编辑器，会生成空下拉）；内置 Agent 的 select 不受影响
const PARAM_TYPES: AgentParamType[] = ['text', 'textarea', 'number', 'project_id']

export function AgentsPage({ layer, projects }: { layer: DataLayer; projects: Project[] }) {
  const [agents, setAgents] = useState<AgentInfo[]>([])
  const [runs, setRuns] = useState<AgentRun[]>([])
  const [templates, setTemplates] = useState<ParamTemplate[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [target, setTarget] = useState<AgentInfo | null>(null)
  const [form, setForm] = useState<Record<string, string>>({})
  const [busy, setBusy] = useState(false)
  const [result, setResult] = useState<AgentRun | null>(null)

  // 新建/编辑自定义 Agent 对话框
  const [createOpen, setCreateOpen] = useState(false)
  const [editingKey, setEditingKey] = useState<string | null>(null)
  const [agentForm, setAgentForm] = useState({ name: '', description: '', prompt: '' })
  const [agentParams, setAgentParams] = useState<AgentDraftParam[]>([emptyParam()])

  // 预置模板：选中回填 / 保存当前表单
  const [templateId, setTemplateId] = useState('')
  const [templateName, setTemplateName] = useState('')
  const [savingTpl, setSavingTpl] = useState(false)

  const refresh = useCallback(async () => {
    try {
      const [a, r, t] = await Promise.all([
        layer.listAgents(),
        layer.listAgentRuns({ page_size: 12 }),
        layer.listParamTemplates(),
      ])
      setAgents(a)
      setRuns(r.items)
      setTemplates(t)
      setError('')
    } catch (e) {
      setError(e instanceof Error ? e.message : '加载失败')
    } finally {
      setLoading(false)
    }
  }, [layer])

  useEffect(() => {
    refresh()
  }, [refresh])

  const openRun = (agent: AgentInfo) => {
    const initial: Record<string, string> = {}
    for (const p of agent.param_schema) {
      const d = p.default
      initial[p.name] = String(d ?? '')
    }
    setForm(initial)
    setResult(null)
    setTemplateId('')
    setTemplateName('')
    setTarget(agent)
  }

  const setField = (name: string, value: string) => setForm((f) => ({ ...f, [name]: value }))

  // 从当前表单收集参数值（数字转 number，空字符串跳过）
  function collectParams(agent: AgentInfo): Record<string, unknown> {
    const params: Record<string, unknown> = {}
    for (const p of agent.param_schema) {
      const raw = form[p.name] ?? ''
      if (p.type === 'number') {
        if (raw !== '') params[p.name] = Number(raw)
      } else if (raw !== '') {
        params[p.name] = raw
      }
    }
    return params
  }

  async function submit() {
    if (!target || busy) return
    setBusy(true)
    setResult(null)
    try {
      const params = collectParams(target)
      const projectId = (params.project_id as string | undefined) || undefined
      const created = await layer.runAgent(target.key, { params, project_id: projectId })
      const run = await pollRun(created.run_id)
      setResult(run)
      await refresh()
    } catch (e) {
      setError(e instanceof Error ? e.message : '运行失败')
    } finally {
      setBusy(false)
    }
  }

  async function pollRun(runId: string, attempts = 60): Promise<AgentRun> {
    for (let i = 0; i < attempts; i++) {
      const run = await layer.getAgentRun(runId)
      if (run.status === 'succeeded' || run.status === 'failed') return run
      await new Promise((r) => setTimeout(r, 1500))
    }
    throw new Error('运行超时')
  }

  const running = useMemo(
    () => runs.filter((r) => r.status === 'pending' || r.status === 'running').length,
    [runs],
  )

  // ---------- 预置模板 ----------

  const agentTemplates = useMemo(
    () => (target ? templates.filter((t) => t.agent_key === target.key) : []),
    [templates, target],
  )

  // 选中模板 → 按参数名回填表单
  const applyTemplate = (id: string) => {
    setTemplateId(id)
    if (!target) return
    const tpl = templates.find((t) => t.id === id)
    if (!tpl) return
    const filled: Record<string, string> = {}
    for (const p of target.param_schema) {
      const v = tpl.params[p.name]
      filled[p.name] = v === undefined || v === null ? '' : String(v)
    }
    setForm(filled)
  }

  async function saveTemplate() {
    if (!target || !templateName.trim() || savingTpl) return
    setSavingTpl(true)
    try {
      const params = collectParams(target)
      const created = await layer.createParamTemplate({
        name: templateName.trim(),
        agent_key: target.key,
        params,
      })
      setTemplates((prev) => [created, ...prev])
      setTemplateName('')
      setTemplateId(created.id)
    } catch (e) {
      setError(e instanceof Error ? e.message : '保存模板失败')
    } finally {
      setSavingTpl(false)
    }
  }

  // ---------- 自定义 Agent CRUD ----------

  const openCreate = () => {
    setEditingKey(null)
    setAgentForm({ name: '', description: '', prompt: '' })
    setAgentParams([emptyParam()])
    setCreateOpen(true)
  }

  const openEdit = (agent: AgentInfo) => {
    setEditingKey(agent.key)
    setAgentForm({ name: agent.name, description: agent.description, prompt: agent.prompt ?? '' })
    setAgentParams(
      agent.param_schema.length
        ? agent.param_schema.map((p) => ({
            name: p.name,
            label: p.label,
            type: p.type,
            required: p.required,
            default: p.default === null || p.default === undefined ? '' : String(p.default),
          }))
        : [emptyParam()],
    )
    setCreateOpen(true)
  }

  const setAgentParam = (i: number, patch: Partial<AgentDraftParam>) =>
    setAgentParams((ps) => ps.map((p, idx) => (idx === i ? { ...p, ...patch } : p)))

  const addAgentParam = () => setAgentParams((ps) => [...ps, emptyParam()])
  const removeAgentParam = (i: number) =>
    setAgentParams((ps) => (ps.length === 1 ? ps : ps.filter((_, idx) => idx !== i)))

  async function submitAgent() {
    if (!agentForm.name.trim() || !agentForm.prompt.trim() || busy) return
    // 参数名重复直接拒绝：重复 key 会让 {{param}} 渲染只取第一个，用户会误以为没生效
    const names = agentParams.map((p) => p.name.trim()).filter(Boolean)
    if (new Set(names).size !== names.length) {
      setError('参数名重复，请修改')
      return
    }
    // 把草稿参数转成 AgentParam（options/placeholder 固定为空）
    const schema: AgentParam[] = agentParams
      .filter((p) => p.name.trim())
      .map((p) => ({
        name: p.name.trim(),
        label: p.label.trim() || p.name.trim(),
        type: p.type,
        required: p.required,
        // 数字默认值：空留空；非数字文本按无效处理为 null，避免 NaN 落库污染渲染
        default:
          p.type === 'number' && p.default !== ''
            ? (Number.isNaN(Number(p.default)) ? null : Number(p.default))
            : p.default === '' ? null : p.default,
        options: [],
        placeholder: '',
      }))
    setBusy(true)
    try {
      if (editingKey) {
        await layer.updateAgent(editingKey, {
          name: agentForm.name.trim(),
          description: agentForm.description.trim() || null,
          prompt: agentForm.prompt.trim(),
          param_schema: schema,
        })
      } else {
        await layer.createAgent({
          name: agentForm.name.trim(),
          description: agentForm.description.trim() || null,
          prompt: agentForm.prompt.trim(),
          param_schema: schema,
        })
      }
      setCreateOpen(false)
      setEditingKey(null)
      await refresh()
    } catch (e) {
      setError(e instanceof Error ? e.message : '保存失败')
    } finally {
      setBusy(false)
    }
  }

  async function deleteCustomAgent(agent: AgentInfo) {
    if (!window.confirm(`确定删除自定义智能体「${agent.name}」？`)) return
    try {
      await layer.deleteAgent(agent.key)
      await refresh()
    } catch (e) {
      setError(e instanceof Error ? e.message : '删除失败')
    }
  }

  return (
    <div className="mx-auto max-w-7xl space-y-6 p-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-[20px] font-[650] tracking-tight text-ink">智能体</h1>
          <p className="mt-1 text-[12.5px] text-ink-3">预置 + 自定义智能体 · 异步运行 · 结果落库</p>
        </div>
        <div className="flex items-center gap-3">
          {runs.length > 0 && (
            <div className="flex items-center gap-3 font-mono text-[11px] tabular-nums text-ink-5">
              <span>{runs.length} 次运行</span>
              {running > 0 && <Badge tone="info">{running} 进行中</Badge>}
            </div>
          )}
          <Button onClick={openCreate}>
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4">
              <path d="M12 5v14M5 12h14" strokeLinecap="round" />
            </svg>
            新建智能体
          </Button>
        </div>
      </div>

      {error && (
        <div className="border-b border-error/20 bg-error/10 px-5 py-1.5 text-[11px] text-error">{error}</div>
      )}

      <section>
        {loading ? (
          <Card className="p-8 text-center text-[12.5px] text-ink-4">加载智能体中…</Card>
        ) : agents.length === 0 ? (
          <Card>
            <Empty title="暂无智能体" hint="后端未就绪或智能体注册失败。" />
          </Card>
        ) : (
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            {agents.map((agent, i) => (
              <Card key={agent.key} className="animate-fadeUp flex flex-col gap-3 p-4" style={{ animationDelay: `${i * 40}ms` }}>
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <div className="text-[14px] font-[600] text-ink">{agent.name}</div>
                    <div className="mt-0.5 font-mono text-[10.5px] uppercase tracking-wide text-ink-5">{agent.key}</div>
                  </div>
                  <Badge tone={agent.source === 'custom' ? 'gold' : 'neutral'}>
                    {agent.source === 'custom' ? '自定义' : '内置'}
                  </Badge>
                </div>
                <p className="line-clamp-2 min-h-[2.5em] text-[12px] leading-relaxed text-ink-3">{agent.description}</p>
                <div className="mt-auto flex flex-wrap gap-1">
                  {agent.param_schema.map((p) => (
                    <span key={p.name} className="rounded border border-line-soft bg-elev1 px-1.5 py-0.5 font-mono text-[10px] text-ink-4">
                      {p.name}
                      {p.required && <span className="text-gold">*</span>}
                    </span>
                  ))}
                </div>
                <div className="flex items-center gap-2">
                  <Button size="sm" className="flex-1" onClick={() => openRun(agent)}>
                    运行
                  </Button>
                  {agent.source === 'custom' && (
                    <>
                      <Button size="sm" variant="secondary" onClick={() => openEdit(agent)}>
                        编辑
                      </Button>
                      <Button size="sm" variant="danger" onClick={() => deleteCustomAgent(agent)}>
                        删除
                      </Button>
                    </>
                  )}
                </div>
              </Card>
            ))}
          </div>
        )}
      </section>

      <section>
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-[13px] font-semibold text-ink-2">运行记录</h2>
          <span className="font-mono text-[11px] tabular-nums text-ink-5">{runs.length} 条</span>
        </div>
        {runs.length === 0 ? (
          <Card>
            <Empty title="还没有运行记录" hint="运行一个智能体后，结果会出现在这里。" />
          </Card>
        ) : (
          <div className="space-y-2">
            {runs.slice(0, 12).map((run) => (
              <Card key={run.id} className="flex flex-wrap items-center gap-3 px-4 py-3">
                <Badge tone={statusTone(run.status)}>{statusLabel[run.status]}</Badge>
                <span className="text-[13px] font-medium text-ink">
                  {agents.find((a) => a.key === run.agent_key)?.name ?? run.agent_key}
                </span>
                {run.project_id && (
                  <span className="rounded border border-line-soft bg-elev1 px-1.5 py-0.5 text-[10.5px] text-ink-4">
                    {projects.find((p) => p.id === run.project_id)?.name ?? run.project_id}
                  </span>
                )}
                <span className="ml-auto font-mono text-[10.5px] tabular-nums text-ink-5">
                  {new Date(run.created_at).toLocaleString()}
                </span>
              </Card>
            ))}
          </div>
        )}
      </section>

      <Dialog open={target !== null} onClose={() => setTarget(null)} title={`运行 · ${target?.name ?? ''}`}>
        <div className="flex max-h-[70vh] flex-col gap-4 overflow-y-auto">
          {target && (
            <div className="flex flex-col gap-1.5">
              <label className="text-[12px] text-ink-3">预置模板</label>
              <div className="flex items-center gap-2">
                <select
                  className="h-9 flex-1 rounded-lg border border-line-soft bg-elev1 px-3 text-[13px] text-ink focus:border-gold-primary/60 focus:outline-none focus:ring-2 focus:ring-gold-primary/25"
                  value={templateId}
                  onChange={(e) => applyTemplate(e.target.value)}
                >
                  <option value="">选择模板回填…</option>
                  {agentTemplates.map((t) => (
                    <option key={t.id} value={t.id}>
                      {t.name}
                    </option>
                  ))}
                </select>
                <Input
                  value={templateName}
                  onChange={(e) => setTemplateName(e.target.value)}
                  placeholder="新模板名"
                  className="w-36"
                />
                <Button size="sm" variant="secondary" onClick={saveTemplate} loading={savingTpl} disabled={!templateName.trim()}>
                  保存为模板
                </Button>
              </div>
            </div>
          )}

          {target &&
            target.param_schema.map((p) => (
              <div key={p.name} className="flex flex-col gap-1.5">
                <label className="text-[12px] text-ink-3">
                  {p.label}
                  {p.required && <span className="ml-0.5 text-gold">*</span>}
                </label>
                {p.type === 'project_id' ? (
                  <select
                    className="h-9 w-full rounded-lg border border-line-soft bg-elev1 px-3 text-[13px] text-ink focus:border-gold-primary/60 focus:outline-none focus:ring-2 focus:ring-gold-primary/25"
                    value={form[p.name] ?? ''}
                    onChange={(e) => setField(p.name, e.target.value)}
                  >
                    <option value="">{p.placeholder || '全部项目'}</option>
                    {projects.map((pr) => (
                      <option key={pr.id} value={pr.id}>
                        {pr.name}
                      </option>
                    ))}
                  </select>
                ) : p.type === 'select' ? (
                  <select
                    className="h-9 w-full rounded-lg border border-line-soft bg-elev1 px-3 text-[13px] text-ink focus:border-gold-primary/60 focus:outline-none focus:ring-2 focus:ring-gold-primary/25"
                    value={form[p.name] ?? ''}
                    onChange={(e) => setField(p.name, e.target.value)}
                  >
                    {p.options.map((o) => (
                      <option key={o.value} value={o.value}>
                        {o.label}
                      </option>
                    ))}
                  </select>
                ) : p.type === 'textarea' ? (
                  <Textarea
                    rows={3}
                    value={form[p.name] ?? ''}
                    onChange={(e) => setField(p.name, e.target.value)}
                    placeholder={p.placeholder}
                  />
                ) : p.type === 'number' ? (
                  <Input
                    type="number"
                    value={form[p.name] ?? ''}
                    onChange={(e) => setField(p.name, e.target.value)}
                    placeholder={p.placeholder}
                  />
                ) : (
                  <Input
                    value={form[p.name] ?? ''}
                    onChange={(e) => setField(p.name, e.target.value)}
                    placeholder={p.placeholder}
                  />
                )}
              </div>
            ))}

          {busy && <div className="text-[12px] text-ink-4">执行中，请稍候…</div>}

          {result && (
            <div className="flex flex-col gap-2 rounded-lg border border-line-soft bg-elev1 p-3">
              <div className="flex items-center gap-2">
                <Badge tone={statusTone(result.status)}>{statusLabel[result.status]}</Badge>
                {result.status === 'failed' && <span className="text-[11px] text-ink-4">运行失败</span>}
              </div>
              {result.status === 'failed' ? (
                <pre className="whitespace-pre-wrap font-mono text-[11.5px] leading-relaxed text-error">{result.error}</pre>
              ) : (
                <pre className="max-h-56 overflow-y-auto whitespace-pre-wrap text-[12px] leading-relaxed text-ink-2">
                  {result.output}
                </pre>
              )}
            </div>
          )}

          <Button onClick={submit} loading={busy} disabled={busy || !!result}>
            运行
          </Button>
        </div>
      </Dialog>

      {/* 新建 / 编辑自定义智能体 */}
      <Dialog open={createOpen} onClose={() => setCreateOpen(false)} title={editingKey ? '编辑智能体' : '新建智能体'}>
        <div className="flex max-h-[70vh] flex-col gap-4 overflow-y-auto">
          <div className="flex flex-col gap-1.5">
            <label className="text-[12px] text-ink-3">名称 *</label>
            <Input
              value={agentForm.name}
              onChange={(e) => setAgentForm((f) => ({ ...f, name: e.target.value }))}
              placeholder="如：代码审查助手"
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <label className="text-[12px] text-ink-3">描述（可选）</label>
            <Input
              value={agentForm.description}
              onChange={(e) => setAgentForm((f) => ({ ...f, description: e.target.value }))}
              placeholder="一句话说明用途"
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <label className="text-[12px] text-ink-3">提示词 *</label>
            <Textarea
              rows={4}
              value={agentForm.prompt}
              onChange={(e) => setAgentForm((f) => ({ ...f, prompt: e.target.value }))}
              placeholder="如：你是资深工程师，{{topic}} 的关键风险有哪些？支持 {{param}} 占位符"
              className="font-mono text-[11.5px]"
            />
          </div>

          <div className="flex flex-col gap-2">
            <div className="flex items-center justify-between">
              <label className="text-[12px] text-ink-3">参数字段</label>
              <Button size="sm" variant="secondary" onClick={addAgentParam}>
                加一个参数
              </Button>
            </div>
            {agentParams.map((p, i) => (
              <div key={i} className="flex flex-col gap-2 rounded-lg border border-line-soft bg-elev1 p-2.5">
                <div className="flex items-center gap-2">
                  <Input
                    value={p.name}
                    onChange={(e) => setAgentParam(i, { name: e.target.value })}
                    placeholder="参数名（如 topic）"
                    className="h-8 flex-1"
                  />
                  <Input
                    value={p.label}
                    onChange={(e) => setAgentParam(i, { label: e.target.value })}
                    placeholder="显示名（可选）"
                    className="h-8 flex-1"
                  />
                  <button onClick={() => removeAgentParam(i)} className="text-ink-4 hover:text-error" title="删除参数">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M18 6 6 18M6 6l12 12" strokeLinecap="round" />
                    </svg>
                  </button>
                </div>
                <div className="flex items-center gap-3">
                  <select
                    className="h-8 w-32 rounded-lg border border-line-soft bg-elev1 px-2 text-[12px] text-ink focus:outline-none"
                    value={p.type}
                    onChange={(e) => setAgentParam(i, { type: e.target.value as AgentParamType })}
                  >
                    {PARAM_TYPES.map((t) => (
                      <option key={t} value={t}>
                        {t}
                      </option>
                    ))}
                  </select>
                  <Input
                    value={p.default}
                    onChange={(e) => setAgentParam(i, { default: e.target.value })}
                    placeholder="默认值（可选）"
                    className="h-8 flex-1 font-mono text-[11.5px]"
                  />
                  <label className="flex cursor-pointer items-center gap-1.5 text-[11.5px] text-ink-3">
                    <input
                      type="checkbox"
                      checked={p.required}
                      onChange={(e) => setAgentParam(i, { required: e.target.checked })}
                    />
                    必填
                  </label>
                </div>
              </div>
            ))}
          </div>

          <Button onClick={submitAgent} loading={busy} disabled={busy || !agentForm.name.trim() || !agentForm.prompt.trim()}>
            {editingKey ? '保存修改' : '创建'}
          </Button>
        </div>
      </Dialog>
    </div>
  )
}
