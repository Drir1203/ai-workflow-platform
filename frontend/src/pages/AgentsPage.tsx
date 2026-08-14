import { useCallback, useEffect, useMemo, useState } from 'react'
import { Badge } from '../components/ui/badge'
import { Button } from '../components/ui/button'
import { Card } from '../components/ui/card'
import { Dialog } from '../components/ui/dialog'
import { Empty } from '../components/ui/empty'
import { Input, Textarea } from '../components/ui/input'
import type { DataLayer } from '../lib/view'
import type { AgentInfo, AgentRun, Project, RunStatus } from '../types'

function statusTone(status: RunStatus) {
  return status === 'succeeded' ? 'success' : status === 'failed' ? 'error' : 'info'
}

const statusLabel: Record<RunStatus, string> = {
  pending: '排队中',
  running: '执行中',
  succeeded: '成功',
  failed: '失败',
}

export function AgentsPage({ layer, projects }: { layer: DataLayer; projects: Project[] }) {
  const [agents, setAgents] = useState<AgentInfo[]>([])
  const [runs, setRuns] = useState<AgentRun[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [target, setTarget] = useState<AgentInfo | null>(null)
  const [form, setForm] = useState<Record<string, string>>({})
  const [busy, setBusy] = useState(false)
  const [result, setResult] = useState<AgentRun | null>(null)

  const refresh = useCallback(async () => {
    try {
      const [a, r] = await Promise.all([layer.listAgents(), layer.listAgentRuns({ page_size: 12 })])
      setAgents(a)
      setRuns(r.items)
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
      initial[p.name] = p.type === 'number' ? String(d ?? '') : String(d ?? '')
    }
    setForm(initial)
    setResult(null)
    setTarget(agent)
  }

  const setField = (name: string, value: string) => setForm((f) => ({ ...f, [name]: value }))

  async function submit() {
    if (!target || busy) return
    setBusy(true)
    setResult(null)
    try {
      const params: Record<string, unknown> = {}
      for (const p of target.param_schema) {
        const raw = form[p.name] ?? ''
        if (p.type === 'number') {
          if (raw !== '') params[p.name] = Number(raw)
        } else if (raw !== '') {
          params[p.name] = raw
        }
      }
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

  return (
    <div className="mx-auto max-w-7xl space-y-6 p-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-[20px] font-[650] tracking-tight text-ink">智能体</h1>
          <p className="mt-1 text-[12.5px] text-ink-3">预置 AI 智能体 · 异步运行 · 结果落库</p>
        </div>
        {runs.length > 0 && (
          <div className="flex items-center gap-3 font-mono text-[11px] tabular-nums text-ink-5">
            <span>{runs.length} 次运行</span>
            {running > 0 && <Badge tone="info">{running} 进行中</Badge>}
          </div>
        )}
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
                <div>
                  <div className="text-[14px] font-[600] text-ink">{agent.name}</div>
                  <div className="mt-0.5 font-mono text-[10.5px] uppercase tracking-wide text-ink-5">{agent.key}</div>
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
                <Button size="sm" onClick={() => openRun(agent)}>
                  运行
                </Button>
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
    </div>
  )
}
