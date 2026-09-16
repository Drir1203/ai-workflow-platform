import { useCallback, useEffect, useRef, useState } from 'react'
import { Badge } from '../components/ui/badge'
import { Button } from '../components/ui/button'
import { Card } from '../components/ui/card'
import { Dialog } from '../components/ui/dialog'
import { Empty } from '../components/ui/empty'
import { Input, Textarea } from '../components/ui/input'
import { Markdown } from '../components/ui/markdown'
import { WorkflowCanvas, type WorkflowCanvasHandle } from '../components/workflow/WorkflowCanvas'
import { WORKFLOW_TEMPLATES } from '../lib/workflowTemplates'
import type { DataLayer } from '../lib/view'
import type { AgentInfo, ParamTemplate, Project, RunStatus, Schedule, Workflow, WorkflowRun } from '../types'

function statusTone(status: RunStatus) {
  return status === 'succeeded' ? 'success' : status === 'failed' ? 'error' : 'info'
}

const statusLabel: Record<RunStatus, string> = {
  pending: '排队中',
  running: '执行中',
  succeeded: '成功',
  failed: '失败',
}

function pad2(n: number): string {
  return String(n).padStart(2, '0')
}

/** 白话时间 → cron：'09:30' → '30 9 * * *'；day 1-7(周一~周日) 表示每周那一天的几点 */
function timeToCron(time: string, day?: string): string {
  const [h, m] = time.split(':').map((x) => Number(x))
  if (day !== undefined) {
    const d = day === '7' ? '0' : day // cron 星期 0=周日
    return `${m} ${h} * * ${d}`
  }
  return `${m} ${h} * * *`
}

/** cron → 白话模式：能识别「每天 HH:MM」「每周 星期 HH:MM」就回填，其余归为高级 */
function cronToSimple(cron: string): { mode: 'daily' | 'weekly' | 'advanced'; time?: string; day?: string } {
  const daily = cron.match(/^(\d{1,2}) (\d{1,2}) \* \* \*$/)
  if (daily) return { mode: 'daily', time: `${pad2(Number(daily[2]))}:${pad2(Number(daily[1]))}` }
  const weekly = cron.match(/^(\d{1,2}) (\d{1,2}) \* \* ([0-7])$/)
  if (weekly) {
    const day = weekly[3] === '0' ? '7' : weekly[3]
    return { mode: 'weekly', time: `${pad2(Number(weekly[2]))}:${pad2(Number(weekly[1]))}`, day }
  }
  return { mode: 'advanced' }
}

function scheduleText(schedule: Workflow['schedule']): string | null {
  if (!schedule) return null
  if (schedule.cron) return `cron ${schedule.cron}`
  if (schedule.interval_minutes) return `每 ${schedule.interval_minutes} 分钟`
  return null
}

export function WorkflowsPage({ layer, projects }: { layer: DataLayer; projects: Project[] }) {
  const [workflows, setWorkflows] = useState<Workflow[]>([])
  const [agents, setAgents] = useState<AgentInfo[]>([])
  const [runs, setRuns] = useState<WorkflowRun[]>([])
  const [templates, setTemplates] = useState<ParamTemplate[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  // 编辑器（新建/编辑共用）：editing=null 表示新建
  const [editorOpen, setEditorOpen] = useState(false)
  const [editing, setEditing] = useState<Workflow | null>(null)
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [enabled, setEnabled] = useState(true)
  const [busy, setBusy] = useState(false)
  const canvasRef = useRef<WorkflowCanvasHandle>(null)

  // 定时调度白话模式：none/interval/daily/weekly/advanced（cron 表达式折叠进「高级」）
  const [schedMode, setSchedMode] = useState<'none' | 'interval' | 'daily' | 'weekly' | 'advanced'>('none')
  const [intervalN, setIntervalN] = useState('15')
  const [dailyTime, setDailyTime] = useState('09:00')
  const [weeklyDay, setWeeklyDay] = useState('1')
  const [weeklyTime, setWeeklyTime] = useState('09:00')
  const [cronRaw, setCronRaw] = useState('')
  // 新建时是否展示「从模板开始」：模板填充或改为空白后隐藏
  const [showTemplates, setShowTemplates] = useState(true)

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

  // 打开新建：清空表单；定时归「不设置」，展示模板选择
  const openCreate = () => {
    setEditing(null)
    setName('')
    setDescription('')
    setEnabled(true)
    setSchedMode('none')
    setIntervalN('15')
    setDailyTime('09:00')
    setWeeklyDay('1')
    setWeeklyTime('09:00')
    setCronRaw('')
    setShowTemplates(true)
    setEditorOpen(true)
  }

  // 打开编辑：回填表单（旧数据无 position 时画布自动水平排布，保存即迁移回写）
  const openEdit = (wf: Workflow) => {
    setEditing(wf)
    setName(wf.name)
    setDescription(wf.description ?? '')
    setEnabled(wf.enabled)
    setShowTemplates(false)
    // schedule → 白话模式回填；识别不了的 cron 归「高级」原样显示
    const sched = wf.schedule
    if (sched?.interval_minutes) {
      setSchedMode('interval')
      setIntervalN(String(sched.interval_minutes))
    } else if (sched?.cron) {
      const parsed = cronToSimple(sched.cron)
      if (parsed.mode === 'daily') {
        setSchedMode('daily')
        setDailyTime(parsed.time ?? '09:00')
      } else if (parsed.mode === 'weekly') {
        setSchedMode('weekly')
        setWeeklyDay(parsed.day ?? '1')
        setWeeklyTime(parsed.time ?? '09:00')
      } else {
        setSchedMode('advanced')
        setCronRaw(sched.cron)
      }
    } else {
      setSchedMode('none')
    }
    setEditorOpen(true)
  }

  // 保存编辑器：画布线性化 → 创建或更新
  async function saveEditor() {
    if (!name.trim() || busy) return
    const linear = canvasRef.current?.linearize()
    if (!linear) return
    if ('error' in linear) {
      setError(linear.error)
      return
    }
    if (linear.steps.length === 0) {
      setError('请先在画布添加至少一个 AI 助手步骤')
      return
    }
    setBusy(true)
    try {
      // 白话定时 → Schedule（cron / interval）；「不设置」则无定时
      let schedule: Schedule | null = null
      if (schedMode === 'interval' && intervalN && Number(intervalN) > 0)
        schedule = { cron: null, interval_minutes: Number(intervalN) }
      else if (schedMode === 'daily') schedule = { cron: timeToCron(dailyTime), interval_minutes: null }
      else if (schedMode === 'weekly') schedule = { cron: timeToCron(weeklyTime, weeklyDay), interval_minutes: null }
      else if (schedMode === 'advanced' && cronRaw.trim())
        schedule = { cron: cronRaw.trim(), interval_minutes: null }
      if (editing) {
        await layer.updateWorkflow(editing.id, {
          name: name.trim(),
          description: description.trim() || undefined,
          steps: linear.steps,
          schedule,
          enabled,
        })
      } else {
        await layer.createWorkflow({
          name: name.trim(),
          description: description.trim() || undefined,
          steps: linear.steps,
          schedule,
        })
      }
      await refresh()
      setEditorOpen(false)
      setEditing(null)
    } catch (e) {
      setError(e instanceof Error ? e.message : '保存失败')
    } finally {
      setBusy(false)
    }
  }

  // 存为预置模板（画布右侧面板透传）
  async function handleSaveTemplate(agentKey: string, tplName: string, params: Record<string, unknown>) {
    try {
      const created = await layer.createParamTemplate({ name: tplName, agent_key: agentKey, params })
      setTemplates((prev) => [created, ...prev])
    } catch (e) {
      setError(e instanceof Error ? e.message : '保存模板失败')
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

  // 仅展示当前 AI 助手里已具备的模板（步骤引用到不存在的 agent_key 则整条模板不可用）
  const availableTemplates = WORKFLOW_TEMPLATES.filter((t) =>
    t.steps.every((s) => agents.some((a) => a.key === s.agent_key)),
  )

  const agentName = (key: string) => agents.find((a) => a.key === key)?.name ?? key

  return (
    <div className="mx-auto max-w-7xl space-y-6 p-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-[20px] font-[650] tracking-tight text-ink">工作流</h1>
          <p className="mt-1 text-[12.5px] text-ink-3">把多个 AI 助手串成一条流水线 · 上一步结果自动传给下一步 · 可定时运行</p>
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
                    <Button size="sm" variant="secondary" onClick={() => openEdit(wf)}>
                      编辑
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
                            <Markdown compact className="rounded-lg bg-elev1 p-2.5">
                              {res.output || '（无输出内容）'}
                            </Markdown>
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

      {/* 编辑器（新建/编辑共用）：顶部基本信息 + 画布 + 底部保存 */}
      <Dialog
        open={editorOpen}
        onClose={() => setEditorOpen(false)}
        title={editing ? '编辑工作流' : '新建工作流'}
        size="xl"
      >
        <div className="flex max-h-[80vh] flex-col gap-4">
          <div className="flex flex-wrap gap-3">
            <div className="min-w-52 flex-1 flex-col gap-1.5">
              <label className="text-[12px] text-ink-3">名称</label>
              <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="如：每日巡检" />
            </div>
            <div className="min-w-52 flex-1 flex-col gap-1.5">
              <label className="text-[12px] text-ink-3">描述（可选）</label>
              <Input value={description} onChange={(e) => setDescription(e.target.value)} placeholder="一句话说明用途" />
            </div>
          </div>

          {/* 从模板开始：给第一次用的用户一键铺好步骤 */}
          {showTemplates && availableTemplates.length > 0 && (
            <div className="flex flex-col gap-1.5">
              <label className="text-[12px] text-ink-3">从模板开始（点一下自动生成步骤）</label>
              <div className="flex flex-wrap gap-2">
                {availableTemplates.map((t) => (
                  <button
                    key={t.id}
                    onClick={() => {
                      canvasRef.current?.loadSteps(t.steps)
                      setShowTemplates(false)
                    }}
                    className="rounded-lg border border-line-soft bg-elev1 px-3 py-2 text-left transition-colors hover:border-gold-primary/50 hover:bg-active"
                  >
                    <div className="text-[12.5px] font-medium text-ink">{t.name}</div>
                    <div className="mt-0.5 text-[11px] leading-snug text-ink-4">{t.desc}</div>
                  </button>
                ))}
                <button
                  onClick={() => setShowTemplates(false)}
                  className="rounded-lg border border-dashed border-line-soft px-3 py-2 text-left transition-colors hover:border-gold-primary/50 hover:bg-active"
                >
                  <div className="text-[12.5px] font-medium text-ink-3">从空白开始</div>
                  <div className="mt-0.5 text-[11px] leading-snug text-ink-4">自己拖拽编排步骤</div>
                </button>
              </div>
            </div>
          )}

          {/* 定时运行白话化：cron 表达式折叠进「高级」 */}
          <div className="flex flex-col gap-1.5">
            <label className="text-[12px] text-ink-3">定时运行（可选）</label>
            <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
              <label className="flex cursor-pointer items-center gap-1.5 text-[12px] text-ink-3">
                <input
                  type="radio"
                  className="accent-gold"
                  checked={schedMode === 'none'}
                  onChange={() => setSchedMode('none')}
                />
                不设置
              </label>
              <label className="flex cursor-pointer items-center gap-1.5 text-[12px] text-ink-3">
                <input
                  type="radio"
                  className="accent-gold"
                  checked={schedMode === 'interval'}
                  onChange={() => setSchedMode('interval')}
                />
                每
                <input
                  type="number"
                  min={1}
                  value={intervalN}
                  onChange={(e) => setIntervalN(e.target.value)}
                  className="h-7 w-16 rounded-lg border border-line-soft bg-elev1 px-2 font-mono text-[12px]"
                />
                分钟
              </label>
              <label className="flex cursor-pointer items-center gap-1.5 text-[12px] text-ink-3">
                <input
                  type="radio"
                  className="accent-gold"
                  checked={schedMode === 'daily'}
                  onChange={() => setSchedMode('daily')}
                />
                每天
                <input
                  type="time"
                  value={dailyTime}
                  onChange={(e) => setDailyTime(e.target.value)}
                  className="h-7 rounded-lg border border-line-soft bg-elev1 px-2 font-mono text-[12px]"
                />
              </label>
              <label className="flex cursor-pointer items-center gap-1.5 text-[12px] text-ink-3">
                <input
                  type="radio"
                  className="accent-gold"
                  checked={schedMode === 'weekly'}
                  onChange={() => setSchedMode('weekly')}
                />
                每周
                <select
                  value={weeklyDay}
                  onChange={(e) => setWeeklyDay(e.target.value)}
                  className="h-7 rounded-lg border border-line-soft bg-elev1 px-1 text-[12px]"
                >
                  {['周一', '周二', '周三', '周四', '周五', '周六', '周日'].map((d, i) => (
                    <option key={i + 1} value={String(i + 1)}>
                      {d}
                    </option>
                  ))}
                </select>
                <input
                  type="time"
                  value={weeklyTime}
                  onChange={(e) => setWeeklyTime(e.target.value)}
                  className="h-7 rounded-lg border border-line-soft bg-elev1 px-2 font-mono text-[12px]"
                />
              </label>
            </div>
            <details className="text-[12px]">
              <summary className="cursor-pointer text-ink-4 hover:text-ink-3">高级（cron 表达式）</summary>
              <div className="mt-1.5 flex items-center gap-2">
                <input
                  type="text"
                  value={cronRaw}
                  onChange={(e) => {
                    setCronRaw(e.target.value)
                    if (e.target.value) setSchedMode('advanced')
                  }}
                  placeholder="如 0 9 * * 1"
                  className="h-8 w-48 rounded-lg border border-line-soft bg-elev1 px-2 font-mono text-[12px]"
                />
                <span className="text-[11px] text-ink-4">填了 cron 即按高级定时</span>
              </div>
            </details>
            <label className="flex cursor-pointer items-center gap-2 text-[12px] text-ink-3">
              <input
                type="checkbox"
                className="accent-gold"
                checked={enabled}
                onChange={(e) => setEnabled(e.target.checked)}
              />
              启用（保存后立即生效）
            </label>
          </div>

          {/* 画布：固定高度防 React Flow 高度塌陷 */}
          <div className="h-[50vh] min-h-[360px]">
            <WorkflowCanvas
              ref={canvasRef}
              initialSteps={editing?.steps ?? []}
              agents={agents}
              projects={projects}
              templates={templates}
              onValidationError={setError}
              onSaveTemplate={handleSaveTemplate}
            />
          </div>

          <Button
            onClick={saveEditor}
            loading={busy}
            disabled={busy || !name.trim() || !agents.length}
          >
            {editing ? '保存修改' : '创建'}
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
                  <Markdown compact className="max-h-44 overflow-y-auto">
                    {res.output || '（无输出内容）'}
                  </Markdown>
                </div>
              ))}
            </>
          )}
        </div>
      </Dialog>
    </div>
  )
}
