import { useState, type DragEvent, type FormEvent } from 'react'
import { cn } from '../lib/cn'
import { Badge } from './ui/badge'
import { Button } from './ui/button'
import { Input } from './ui/input'
import { priorityLabel, priorityTone } from './status'
import type { Task } from '../types'

/** 看板三列：任务状态 → 中文列名（与 TaskItem 的文案保持一致） */
const TASK_COLUMNS = [
  { status: 'todo', label: '待办' },
  { status: 'in_progress', label: '进行中' },
  { status: 'done', label: '已完成' },
] as const

interface KanbanBoardProps {
  tasks: Task[]
  projectId: string
  onMoveTask: (task: Task, status: string) => Promise<void>
  onCreateTask: (t: { project_id: string; title: string; priority?: string; status?: string }) => Promise<void>
  onDeleteTask: (id: string) => Promise<void>
}

/**
 * 拖拽看板：三列（待办/进行中/已完成）。
 * 拖拽卡片跨列 = 改任务状态（复用 PATCH /api/tasks/{id}，后端零改动）。
 * 拖放实现复用 WorkflowCanvas 已验证的原生 HTML5 DnD 模式，零额外依赖。
 */
export function KanbanBoard({ tasks, projectId, onMoveTask, onCreateTask, onDeleteTask }: KanbanBoardProps) {
  // 落点处理放父级：列组件只拿到本列任务，需在这里用全量 tasks 把 id 还原成 task
  function handleDrop(colStatus: string, e: DragEvent<HTMLDivElement>) {
    e.preventDefault()
    const id = e.dataTransfer.getData('application/x-task-id')
    if (!id) return
    const task = tasks.find((t) => t.id === id)
    if (!task || task.status === colStatus) return
    void onMoveTask(task, colStatus)
  }

  return (
    <div className="grid grid-cols-1 gap-3 p-3 sm:grid-cols-3">
      {TASK_COLUMNS.map((col) => (
        <KanbanColumn
          key={col.status}
          column={col}
          tasks={tasks.filter((t) => t.status === col.status)}
          projectId={projectId}
          onCreateTask={onCreateTask}
          onDeleteTask={onDeleteTask}
          onDrop={(e) => handleDrop(col.status, e)}
        />
      ))}
    </div>
  )
}

function KanbanColumn({
  column,
  tasks,
  projectId,
  onCreateTask,
  onDeleteTask,
  onDrop,
}: {
  column: { status: string; label: string }
  tasks: Task[]
  projectId: string
  onCreateTask: KanbanBoardProps['onCreateTask']
  onDeleteTask: KanbanBoardProps['onDeleteTask']
  onDrop: (e: DragEvent<HTMLDivElement>) => void
}) {
  const [over, setOver] = useState(false)
  const [adding, setAdding] = useState(false)
  const [title, setTitle] = useState('')
  const [priority, setPriority] = useState('medium')

  function submit(e: FormEvent) {
    e.preventDefault()
    if (!title.trim()) return
    void onCreateTask({ project_id: projectId, title: title.trim(), priority, status: column.status })
    setTitle('')
    setPriority('medium')
    setAdding(false)
  }

  return (
    <div
      onDragOver={(e) => {
        // 必须 preventDefault，否则浏览器拒绝触发 drop
        e.preventDefault()
        e.dataTransfer.dropEffect = 'move'
        setOver(true)
      }}
      onDrop={(e) => {
        setOver(false)
        onDrop(e)
      }}
      onDragEnter={() => setOver(true)}
      onDragLeave={(e) => {
        // 移入列内子元素也算 dragleave，用 relatedTarget 判断是否真的离开整列，避免高亮闪烁
        if (e.currentTarget.contains(e.relatedTarget as Node)) return
        setOver(false)
      }}
      className={cn(
        'flex min-h-[160px] flex-col rounded-lg border bg-elev1 transition-colors',
        over ? 'border-gold-primary/60 bg-gold-tint/20' : 'border-line-soft',
      )}
    >
      <div className="flex items-center gap-2 border-b border-line px-3 py-2">
        <span className="text-[12px] font-semibold text-ink-2">{column.label}</span>
        <span className="rounded-full bg-elev2 px-1.5 py-0.5 font-mono text-[10px] tabular-nums text-ink-4">
          {tasks.length}
        </span>
      </div>

      {/* 任务区独立滚动：多任务时列内容在 Card 内滚动，不撑破外层 Card 的 overflow-hidden */}
      <div className="max-h-[440px] flex-1 space-y-2 overflow-y-auto p-2">
        {tasks.length === 0 ? (
          <div className="py-6 text-center text-[11px] text-ink-5">拖拽任务到这里</div>
        ) : (
          tasks.map((t) => <TaskCard key={t.id} task={t} onDelete={onDeleteTask} />)
        )}
      </div>

      {adding ? (
        <form onSubmit={submit} className="space-y-2 border-t border-line p-2">
          <Input
            autoFocus
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="任务标题"
            className="h-8"
          />
          <div className="flex items-center gap-2">
            <select
              value={priority}
              onChange={(e) => setPriority(e.target.value)}
              className="h-8 rounded-lg border border-line-soft bg-elev1 px-2 text-[12px] text-ink-2 focus:border-gold-primary/60 focus:outline-none"
            >
              <option value="high">高</option>
              <option value="medium">中</option>
              <option value="low">低</option>
            </select>
            <Button size="sm" type="submit" disabled={!title.trim()} className="flex-1">
              添加
            </Button>
          </div>
        </form>
      ) : (
        <button
          onClick={() => setAdding(true)}
          className="border-t border-line px-3 py-2 text-left text-[11px] text-ink-4 transition-colors hover:bg-active hover:text-ink"
        >
          + 添加
        </button>
      )}
    </div>
  )
}

function TaskCard({ task, onDelete }: { task: Task; onDelete: (id: string) => Promise<void> }) {
  const done = task.status === 'done'
  return (
    <div
      draggable
      onDragStart={(e) => {
        e.dataTransfer.setData('application/x-task-id', task.id)
        e.dataTransfer.effectAllowed = 'move'
      }}
      className="group cursor-grab rounded-md border border-line-soft bg-bg p-2.5 shadow-sm transition-[border-color] hover:border-gold-primary/40 active:cursor-grabbing"
    >
      <div className="flex items-start justify-between gap-2">
        <div className={cn('min-w-0 break-words text-[12.5px] leading-snug', done ? 'text-ink-4 line-through' : 'text-ink')}>
          {task.title}
        </div>
        <button
          onClick={() => void onDelete(task.id)}
          aria-label="删除任务"
          className="hidden h-5 w-5 shrink-0 items-center justify-center rounded text-ink-5 transition-colors hover:bg-error/10 hover:text-error group-hover:flex"
        >
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M18 6 6 18M6 6l12 12" strokeLinecap="round" />
          </svg>
        </button>
      </div>
      <div className="mt-1.5 flex flex-wrap items-center gap-2 text-[10.5px]">
        <Badge tone={priorityTone(task.priority)}>{priorityLabel(task.priority)}</Badge>
        {task.due_date && <span className="font-mono tabular-nums text-ink-5">due {task.due_date}</span>}
      </div>
    </div>
  )
}
