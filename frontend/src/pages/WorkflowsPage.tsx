import { useCallback, useEffect, useState } from 'react'
import { Badge } from '../components/ui/badge'
import { Button } from '../components/ui/button'
import { Card } from '../components/ui/card'
import { Dialog } from '../components/ui/dialog'
import { Empty } from '../components/ui/empty'
import { Input, Textarea } from '../components/ui/input'
import type { DataLayer } from '../lib/view'
import type { AgentInfo, ParamTemplate, Project, RunStatus, Workflow, WorkflowRun } from '../types'

function statusTone(status: RunStatus) {
  return status === 'succeeded' ? 'success' : status === 'failed' ? 'error' : 'info'
}

const statusLabel: Record<RunStatus, string> = {
  pending: '排队中',
  running: '执行中',
  succeeded: '成功',
  failed: '失败',
}

function scheduleText(schedule: Workflow['schedule']): string | null {
  if (!schedule) return null
  if (schedule.cron) return `cron ${schedule.cron}`
  if (schedule.interval_minutes) return `每 ${schedule.interval_minutes} 分钟`
  return null
}

interface StepDraft {
  label: string
  agent_key: string
  paramsJson: string
  tplId: string // 编辑态：当前选中的预置模板（不提交给后端）
}

export function WorkflowsPage({ layer, projects }: { layer: DataLayer; projects: Project[] }) {
  const [workflows, setWorkflows] = useState<Workflow[]>([])
  const [agents, setAgents] = useState<AgentInfo[]>([])
  const [runs, setRuns] = useState<WorkflowRun[]>([])
  const [templates, setTemplates] = useState<ParamTemplate[]>([])
  const [tplName, setTplName] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const [createOpen, setCreateOpen] = useState(false)
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [steps, setSteps] = useState<StepDraft[]>([{ label: '', agent_key: '', paramsJson: '', tplId: '' }])
  const [cron, setCron] = useState('')
  const [intervalMinutes, setIntervalMinutes] = useState('')
  const [enabled, setEnabled] = useState(true)
  const [busy, setBusy] = useState(false)

  const [runningId, setRunningId] = useState<string | null>(null)
  const [runResult, setRunResult] = useState<WorkflowRun | null>(null)
  // 运行记录中当前展开的一条（点击行可展开/收起，展示各步骤输出）
  const [expandedRunId, setExpandedRunId] = useState<string | null>(null)

  const refresh = useCallback(async () => {
    try {
      const [w, a, r, t] = await Promise.all([
        layer.listWorkflows(),
        layer.listAgents(),
        layer.listWorkflowRuns({ page_size: 12 }),
        layer.listParamTemplates(),
      ])
      setWorkflows(w)
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

  const setStep = (i: number, patch: Partial<StepDraft>) =>
    setSteps((s) => s.map((step, idx) => (idx === i ? { ...step, ...patch } : step)))

  // 打开弹窗时重置草稿，避免上次取消/成功后残留旧输入（关闭不清空，只是不再显示）
  const openCreate = () => {
    setName('')
    setDescription('')
    setSteps([{ label: '', agent_key: '', paramsJson: '', tplId: '' }])
    setCron('')
    setIntervalMinutes('')
    setEnabled(true)
    setTplName('')
    setCreateOpen(true)
  }

  const addStep = () => setSteps((s) => [...s, { label: '', agent_key: '', paramsJson: '', tplId: '' }])
  const removeStep = (i: number) => setSteps((s) => (s.length === 1 ? s : s.filter((_, idx) => idx !== i)))

  // 选中预置模板 → 把模板参数 JSON 填进 paramsJson（可按需再改）
  const applyStepTemplate = (i: number, id: string) => {
    setStep(i, { tplId: id })
    const tpl = templates.find((t) => t.id === id)
    if (!tpl) return
    setStep(i, { paramsJson: JSON.stringify(tpl.params ?? {}, null, 2) })
  }

  // 把当前步骤的参数保存为命名模板，供后续复用
  async function saveStepTemplate(i: number) {
    const s = steps[i]
    if (!s?.agent_key || !tplName.trim() || busy) return
    let params: Record<string, unknown> = {}
    if (s.paramsJson.trim()) {
      try {
        params = JSON.parse(s.paramsJson)
      } catch {
        // 参数不是合法 JSON 时明确报错，避免静默存成空模板
        setError(`步骤 ${i + 1} 的参数 JSON 格式错误`)
        return
      }
    }
    setBusy(true)
    try {
      const created = await layer.createParamTemplate({ name: tplName.trim(), agent_key: s.agent_key, params })
      setTemplates((prev) => [created, ...prev])
      setTplName('')
    } catch (e) {
      setError(e instanceof Error ? e.message : '保存模板失败')
    } finally {
      setBusy(false)
    }
  }

  async function submitCreate() {
    if (!name.trim() || steps.some((s) => !s.agent_key) || busy) return
    setBusy(true)
    try {
      const parsedSteps = steps.map((s) => {
        let params: Record<string, unknown> = {}
        if (s.paramsJson.trim()) {
          try {
            params = JSON.parse(s.paramsJson)
          } catch {
            // 参数 JSON 非法：抛错中止创建（由外层 catch 显示到错误条）
            throw new Error(`步骤「${s.label.trim() || s.agent_key}」的参数 JSON 格式错误`)
          }
        }
        return { label: s.label.trim() || s.agent_key, agent_key: s.agent_key, params }
      })
      let schedule: { cron?: string; interval_minutes?: number } | null = null
      if (cron.trim()) schedule = { cron: cron.trim() }
      else if (intervalMinutes.trim() && Number(intervalMinutes) > 0)
        schedule = { interval_minutes: Number(intervalMinutes) }
      await layer.createWorkflow({
        name: name.trim(),
        description: description.trim() || undefined,
        steps: parsedSteps,
        schedule,
      })
      await refresh()
      setCreateOpen(false)
      setName('')
      setDescription('')
      setSteps([{ label: '', agent_key: '', paramsJson: '', tplId: '' }])
      setCron('')
      setIntervalMinutes('')
      setEnabled(true)
      setTplName('')
    } catch (e) {
      setError(e instanceof Error ? e.message : '创建失败')
    } finally {
      setBusy(false)
    }
  }

  async function runWorkflow(id: string) {
    if (runningId) return
    setRunningId(id)
    setRunResult(null)
    try {
      const created = await layer.runWorkflow(id)
      const run = await pollWorkflowRun(created.run_id)
      if (run.status === 'failed') {
        // 失败：留在弹窗内展示错误详情，便于定位原因
        setRunResult(run)
        return
      }
      // 成功：自动关闭运行结果弹窗，并在下方运行记录里展开最新一条展示各步骤输出
      setRunResult(null)
      setExpandedRunId(run.id)
      await refresh()
    } catch (e) {
      setError(e instanceof Error ? e.message : '运行失败')
    } finally {
      setRunningId(null)
    }
  }

  async function pollWorkflowRun(runId: string, attempts = 60): Promise<WorkflowRun> {
    for (let i = 0; i < attempts; i++) {
      const run = await layer.getWorkflowRun(runId)
      if (run.status === 'succeeded' || run.status === 'failed') return run
      await new Promise((r) => setTimeout(r, 1500))
    }
    throw new Error('运行超时')
  }

  async function deleteWorkflow(id: string) {
    if (!window.confirm('确定删除这个工作流？')) return
    try {
      await layer.deleteWorkflow(id)
      await refresh()
    } catch (e) {
      setError(e instanceof Error ? e.message : '删除失败')
    }
  }

  async function toggleEnabled(wf: Workflow) {
    try {
      await layer.updateWorkflow(wf.id, { enabled: !wf.enabled })
      await refresh()
    } catch (e) {
      setError(e instanceof Error ? e.message : '更新失败')
    }
  }

  const agentName = (key: string) => agents.find((a) => a.key === key)?.name ?? key

  return (
    <div className="mx-auto max-w-7xl space-y-6 p-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-[20px] font-[650] tracking-tight text-ink">工作流</h1>
          <p className="mt-1 text-[12.5px] text-ink-3">多步 Agent 编排 · 上一步输出注入下一步 · 定时触发</p>
        </div>
        <Button onClick={openCreate}>
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4">
            <path d="M12 5v14M5 12h14" strokeLinecap="round" />
          </svg>
          新建工作流
        </Button>
      </div>

      {error && (
        <div className="border-b border-error/20 bg-error/10 px-5 py-1.5 text-[11px] text-error">{error}</div>
      )}

      <section>
        {loading ? (
          <Card className="p-8 text-center text-[12.5px] text-ink-4">加载工作流中…</Card>
        ) : workflows.length === 0 ? (
          <Card>
            <Empty
              title="还没有工作流"
              hint="把多个智能体编排成一条流水线，支持手动与定时触发。"
              action={
                <Button size="sm" onClick={openCreate}>
                  新建工作流
                </Button>
              }
            />
          </Card>
        ) : (
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
            {workflows.map((wf) => {
              const sched = scheduleText(wf.schedule)
              return (
                <Card key={wf.id} className="flex flex-col gap-3 p-4">
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <div className="text-[14px] font-[600] text-ink">{wf.name}</div>
                      <div className="mt-0.5 font-mono text-[10.5px] uppercase tracking-wide text-ink-5">{wf.id.slice(0, 8)}</div>
                    </div>
                    <button onClick={() => toggleEnabled(wf)} className="cursor-pointer" title={wf.enabled ? '停用' : '启用'}>
                      <Badge tone={wf.enabled ? 'success' : 'neutral'}>{wf.enabled ? '已启用' : '已停用'}</Badge>
                    </button>
                  </div>
                  {wf.description && (
                    <p className="line-clamp-2 text-[12px] leading-relaxed text-ink-3">{wf.description}</p>
                  )}
                  <div className="flex flex-wrap gap-1">
                    {wf.steps.map((s, i) => (
                      <span key={`${s.agent_key}-${i}`} className="flex items-center gap-1">
                        <span className="rounded border border-line-soft bg-elev1 px-1.5 py-0.5 font-mono text-[10px] text-ink-4">
                          {i + 1}. {agentName(s.agent_key)}
                        </span>
                        {i < wf.steps.length - 1 && <span className="text-[10px] text-ink-5">→</span>}
                      </span>
                    ))}
                  </div>
                  {sched ? (
                    <span className="font-mono text-[10.5px] text-gold">{sched}</span>
                  ) : (
                    <span className="text-[10.5px] text-ink-5">无定时 · 手动触发</span>
                  )}
                  <div className="mt-auto flex items-center gap-2">
                    <Button
                      size="sm"
                      loading={runningId === wf.id}
                      disabled={!!runningId}
                      onClick={() => runWorkflow(wf.id)}
                    >
                      立即运行
                    </Button>
                    <Button size="sm" variant="danger" onClick={() => deleteWorkflow(wf.id)}>
                      删除
                    </Button>
                  </div>
                </Card>
              )
            })}
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
            <Empty title="还没有运行记录" hint="运行一个工作流后，结果会出现在这里。" />
          </Card>
        ) : (
          <div className="space-y-2">
            {runs.slice(0, 12).map((run) => {
              const open = expandedRunId === run.id
              return (
                <Card key={run.id} className="overflow-hidden px-4 py-3">
                  <button
                    onClick={() => setExpandedRunId(open ? null : run.id)}
                    className="flex w-full flex-wrap items-center gap-3 text-left"
                  >
                    <Badge tone={statusTone(run.status)}>{statusLabel[run.status]}</Badge>
                    <span className="text-[13px] font-medium text-ink">
                      {workflows.find((w) => w.id === run.workflow_id)?.name ?? run.workflow_id.slice(0, 8)}
                    </span>
                    <Badge tone="neutral">{run.triggered_by === 'scheduled' ? '定时' : '手动'}</Badge>
                    <span className="ml-auto flex items-center gap-2 font-mono text-[10.5px] tabular-nums text-ink-5">
                      {new Date(run.created_at).toLocaleString()}
                      <svg
                        width="12"
                        height="12"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="2"
                        className={`transition-transform duration-150 ${open ? 'rotate-180' : ''}`}
                      >
                        <path d="m6 9 6 6 6-6" strokeLinecap="round" strokeLinejoin="round" />
                      </svg>
                    </span>
                  </button>
                  {open && (
                    <div className="mt-3 space-y-2 border-t border-line pt-3">
                      {run.status === 'failed' && run.error && (
                        <pre className="whitespace-pre-wrap font-mono text-[11.5px] leading-relaxed text-error">
                          {run.error}
                        </pre>
                      )}
                      {run.results?.length ? (
                        run.results.map((res, i) => (
                          <div key={i} className="flex flex-col gap-1">
                            <div className="text-[11px] font-medium text-ink-3">
                              {res.label || agentName(res.agent_key)}
                              <span className="ml-1.5 font-mono text-[10px] text-ink-5">{res.agent_key}</span>
                            </div>
                            <pre className="whitespace-pre-wrap rounded-lg bg-elev1 p-2.5 text-[12px] leading-relaxed text-ink-2">
                              {res.output ?? '（无输出内容）'}
                            </pre>
                          </div>
                        ))
                      ) : (
                        <div className="text-[12px] text-ink-4">（无步骤输出）</div>
                      )}
                    </div>
                  )}
                </Card>
              )
            })}
          </div>
        )}
      </section>

      {/* 新建工作流 */}
      <Dialog open={createOpen} onClose={() => setCreateOpen(false)} title="新建工作流">
        <div className="flex max-h-[70vh] flex-col gap-4 overflow-y-auto">
          <div className="flex flex-col gap-1.5">
            <label className="text-[12px] text-ink-3">名称</label>
            <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="如：每日巡检" />
          </div>
          <div className="flex flex-col gap-1.5">
            <label className="text-[12px] text-ink-3">描述（可选）</label>
            <Textarea rows={2} value={description} onChange={(e) => setDescription(e.target.value)} placeholder="一句话说明用途" />
          </div>

          <div className="flex flex-col gap-2">
            <div className="flex items-center justify-between">
              <label className="text-[12px] text-ink-3">步骤</label>
              <Button size="sm" variant="secondary" onClick={addStep}>
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4">
                  <path d="M12 5v14M5 12h14" strokeLinecap="round" />
                </svg>
                加一步
              </Button>
            </div>
            {steps.map((s, i) => (
              <div key={i} className="flex flex-col gap-1.5 rounded-lg border border-line-soft bg-elev1 p-2.5">
                <div className="flex items-center gap-2">
                  <span className="font-mono text-[10px] text-ink-5">{i + 1}</span>
                  <Input
                    value={s.label}
                    onChange={(e) => setStep(i, { label: e.target.value })}
                    placeholder="步骤名（可选）"
                    className="h-8"
                  />
                  <button onClick={() => removeStep(i)} className="text-ink-4 hover:text-error" title="删除步骤">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M18 6 6 18M6 6l12 12" strokeLinecap="round" />
                    </svg>
                  </button>
                </div>
                <select
                  className="h-9 w-full rounded-lg border border-line-soft bg-elev1 px-3 text-[13px] text-ink focus:border-gold-primary/60 focus:outline-none focus:ring-2 focus:ring-gold-primary/25"
                  value={s.agent_key}
                  onChange={(e) => setStep(i, { agent_key: e.target.value, tplId: '' })}
                >
                  <option value="">选择智能体…</option>
                  {agents.map((a) => (
                    <option key={a.key} value={a.key}>
                      {a.name}（{a.key}）
                    </option>
                  ))}
                </select>
                <div className="flex items-center gap-2">
                  <select
                    className="h-8 flex-1 rounded-lg border border-line-soft bg-elev1 px-2 font-mono text-[11.5px] text-ink focus:outline-none disabled:opacity-50"
                    value={s.tplId}
                    onChange={(e) => applyStepTemplate(i, e.target.value)}
                    disabled={!s.agent_key}
                  >
                    <option value="">模板回填…</option>
                    {templates
                      .filter((t) => t.agent_key === s.agent_key)
                      .map((t) => (
                        <option key={t.id} value={t.id}>
                          {t.name}
                        </option>
                      ))}
                  </select>
                  <Input
                    value={tplName}
                    onChange={(e) => setTplName(e.target.value)}
                    placeholder="存为模板名"
                    className="h-8 w-32 font-mono text-[11.5px]"
                    disabled={!s.agent_key}
                  />
                  <Button
                    size="sm"
                    variant="secondary"
                    onClick={() => saveStepTemplate(i)}
                    disabled={!s.agent_key || !tplName.trim()}
                    loading={busy}
                  >
                    存为模板
                  </Button>
                </div>
                <Textarea
                  rows={2}
                  value={s.paramsJson}
                  onChange={(e) => setStep(i, { paramsJson: e.target.value })}
                  placeholder='参数 JSON（可选），可用 {{step.0.output}} / {{prev_output}} 引用上一步输出'
                  className="font-mono text-[11.5px]"
                />
              </div>
            ))}
          </div>

          <div className="flex flex-col gap-2 rounded-lg border border-line-soft bg-elev1 p-2.5">
            <label className="text-[12px] text-ink-3">定时调度（可选，二选一）</label>
            <Input value={cron} onChange={(e) => setCron(e.target.value)} placeholder="cron 表达式，如 0 9 * * 1" className="font-mono text-[12px]" />
            <div className="flex items-center gap-2">
              <Input
                type="number"
                value={intervalMinutes}
                onChange={(e) => setIntervalMinutes(e.target.value)}
                placeholder="间隔分钟"
                className="font-mono text-[12px]"
              />
              <span className="text-[11px] text-ink-4">分钟</span>
            </div>
            <label className="flex cursor-pointer items-center gap-2 text-[12px] text-ink-3">
              <input type="checkbox" checked={enabled} onChange={(e) => setEnabled(e.target.checked)} />
              启用
            </label>
          </div>

          <Button onClick={submitCreate} loading={busy} disabled={busy || !name.trim() || steps.some((s) => !s.agent_key)}>
            创建
          </Button>
        </div>
      </Dialog>

      {/* 运行结果 */}
      <Dialog open={runResult !== null} onClose={() => setRunResult(null)} title="运行结果">
        <div className="flex max-h-[70vh] flex-col gap-3 overflow-y-auto">
          {runResult && (
            <>
              <div className="flex items-center gap-2">
                <Badge tone={statusTone(runResult.status)}>{statusLabel[runResult.status]}</Badge>
                {runResult.triggered_by === 'scheduled' && <Badge tone="neutral">定时</Badge>}
              </div>
              {runResult.status === 'failed' && (
                <pre className="whitespace-pre-wrap rounded-lg border border-error/20 bg-error/10 p-3 font-mono text-[11.5px] leading-relaxed text-error">
                  {runResult.error}
                </pre>
              )}
              {runResult.results?.map((res, i) => (
                <div key={i} className="flex flex-col gap-1.5 rounded-lg border border-line-soft bg-elev1 p-3">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-[10px] text-ink-5">{i + 1}</span>
                    <span className="text-[12.5px] font-medium text-ink">{res.label}</span>
                    <span className="font-mono text-[10px] text-ink-5">{agentName(res.agent_key)}</span>
                  </div>
                  <pre className="max-h-44 overflow-y-auto whitespace-pre-wrap text-[12px] leading-relaxed text-ink-2">
                    {res.output}
                  </pre>
                </div>
              ))}
            </>
          )}
        </div>
      </Dialog>
    </div>
  )
}
