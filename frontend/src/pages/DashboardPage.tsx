import { useMemo, useState } from 'react'
import { ProjectCard } from '../components/ProjectCard'
import { Button } from '../components/ui/button'
import { Card } from '../components/ui/card'
import { Dialog } from '../components/ui/dialog'
import { Empty } from '../components/ui/empty'
import { Input, Textarea } from '../components/ui/input'
import type { Note, Project, Task } from '../types'

function StatCard({ label, value, sub }: { label: string; value: string | number; sub?: string }) {
  return (
    <Card className="p-4">
      <div className="text-[11px] text-ink-4">{label}</div>
      <div className="text-glow mt-1.5 font-mono text-[24px] font-semibold tabular-nums text-gold">
        {value}
      </div>
      {sub && <div className="mt-0.5 text-[11px] text-ink-5">{sub}</div>}
    </Card>
  )
}

export function DashboardPage({
  projects,
  tasks,
  notes,
  onOpenProject,
  onCreateProject,
}: {
  projects: Project[]
  tasks: Task[]
  notes: Note[]
  onOpenProject: (id: string) => void
  onCreateProject: (name: string, description?: string, repoUrl?: string, deployUrl?: string) => Promise<void>
}) {
  const [open, setOpen] = useState(false)
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [repoUrl, setRepoUrl] = useState('')
  const [deployUrl, setDeployUrl] = useState('')
  const [busy, setBusy] = useState(false)

  const stats = useMemo(() => {
    const total = tasks.length
    const done = tasks.filter((t) => t.status === 'done').length
    const inProgress = tasks.filter((t) => t.status === 'in_progress').length
    const today = new Date().toISOString().slice(0, 10)
    const todayDue = tasks.filter((t) => t.due_date === today).length
    const rate = total ? Math.round((done / total) * 1000) / 10 : 0
    return {
      active: projects.filter((p) => p.status === 'active').length,
      inProgress,
      todayDue,
      rate,
      total,
      done,
    }
  }, [tasks, projects])

  async function submit() {
    if (!name.trim() || busy) return
    setBusy(true)
    try {
      await onCreateProject(name.trim(), description.trim() || undefined, repoUrl.trim() || undefined, deployUrl.trim() || undefined)
      setOpen(false)
      setName('')
      setDescription('')
      setRepoUrl('')
      setDeployUrl('')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="mx-auto max-w-7xl space-y-6 p-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-[20px] font-[650] tracking-tight text-ink">工作台</h1>
          <p className="mt-1 text-[12.5px] text-ink-3">管理项目、任务与笔记 · 数据由 AI 引擎驱动</p>
        </div>
        <Button onClick={() => setOpen(true)}>
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4">
            <path d="M12 5v14M5 12h14" strokeLinecap="round" />
          </svg>
          新建项目
        </Button>
      </div>

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatCard label="活跃项目" value={stats.active} sub={`${projects.length} 个全部`} />
        <StatCard label="进行中任务" value={stats.inProgress} sub={`${stats.total} 个总计`} />
        <StatCard label="今日截止" value={stats.todayDue} sub="due today" />
        <StatCard label="完成率" value={`${stats.rate}%`} sub={`${stats.done} / ${stats.total} 已完成`} />
      </div>

      <section>
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-[13px] font-semibold text-ink-2">项目</h2>
          <span className="font-mono text-[11px] tabular-nums text-ink-5">{projects.length} 个</span>
        </div>
        {projects.length === 0 ? (
          <Card>
            <Empty
              title="还没有项目"
              hint="创建一个项目，开始组织你的任务与笔记。"
              action={
                <Button size="sm" onClick={() => setOpen(true)}>
                  新建项目
                </Button>
              }
            />
          </Card>
        ) : (
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
            {projects.map((p, i) => (
              <div key={p.id} className="animate-fadeUp" style={{ animationDelay: `${i * 30}ms` }}>
                <ProjectCard
                  project={p}
                  tasks={tasks.filter((t) => t.project_id === p.id)}
                  notes={notes.filter((n) => n.project_id === p.id)}
                  onOpen={() => onOpenProject(p.id)}
                />
              </div>
            ))}
          </div>
        )}
      </section>

      <Dialog open={open} onClose={() => setOpen(false)} title="新建项目">
        <div className="flex flex-col gap-4">
          <div className="flex flex-col gap-1.5">
            <label className="text-[12px] text-ink-3">项目名称</label>
            <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="如：CrossBorder AI" autoFocus />
          </div>
          <div className="flex flex-col gap-1.5">
            <label className="text-[12px] text-ink-3">描述（可选）</label>
            <Textarea rows={2} value={description} onChange={(e) => setDescription(e.target.value)} placeholder="一句话说明这个项目" />
          </div>
          <div className="flex flex-col gap-1.5">
            <label className="text-[12px] text-ink-3">仓库地址（可选）</label>
            <Input value={repoUrl} onChange={(e) => setRepoUrl(e.target.value)} placeholder="https://github.com/…" />
          </div>
          <div className="flex flex-col gap-1.5">
            <label className="text-[12px] text-ink-3">部署地址（可选）</label>
            <Input value={deployUrl} onChange={(e) => setDeployUrl(e.target.value)} placeholder="https://… 线上地址" />
          </div>
          <Button onClick={submit} loading={busy} disabled={!name.trim()}>
            创建
          </Button>
        </div>
      </Dialog>
    </div>
  )
}
