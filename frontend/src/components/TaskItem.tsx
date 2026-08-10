import { cn } from '../lib/cn'
import { Badge } from './ui/badge'
import { priorityLabel, priorityTone } from './status'
import type { Task } from '../types'

export function TaskItem({
  task,
  onToggle,
  onDelete,
}: {
  task: Task
  onToggle: () => void
  onDelete: () => void
}) {
  const done = task.status === 'done'
  return (
    <div className="group flex items-start gap-3 border-b border-line px-4 py-3 last:border-0">
      <button
        onClick={onToggle}
        aria-label={done ? '标记为未完成' : '标记为完成'}
        className={cn(
          'mt-0.5 flex h-[18px] w-[18px] shrink-0 items-center justify-center rounded-md border transition-[background-color,border-color] duration-150',
          done
            ? 'border-transparent bg-gradient-to-br from-gold to-gold-deep'
            : 'border-line-soft hover:border-gold-primary/50',
        )}
      >
        {done && (
          <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="#1A1406" strokeWidth="3.4">
            <path d="M4 12.5 9.5 18 20 6.5" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        )}
      </button>
      <div className="min-w-0 flex-1">
        <div className={cn('text-[13px] leading-snug', done ? 'text-ink-4 line-through' : 'text-ink')}>
          {task.title}
        </div>
        {task.description && (
          <div className="mt-0.5 line-clamp-1 text-[12px] text-ink-4">{task.description}</div>
        )}
        <div className="mt-1.5 flex flex-wrap items-center gap-2 text-[11px]">
          <Badge tone={priorityTone(task.priority)}>{priorityLabel(task.priority)}</Badge>
          {task.due_date && (
            <span className="font-mono tabular-nums text-ink-5">due {task.due_date}</span>
          )}
          <span className="text-ink-5">{task.status === 'in_progress' ? '进行中' : task.status === 'done' ? '已完成' : '待办'}</span>
        </div>
      </div>
      <button
        onClick={onDelete}
        aria-label="删除任务"
        className="hidden h-6 w-6 shrink-0 items-center justify-center rounded-md text-ink-5 transition-colors hover:bg-error/10 hover:text-error group-hover:flex"
      >
        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M18 6 6 18M6 6l12 12" strokeLinecap="round" />
        </svg>
      </button>
    </div>
  )
}
