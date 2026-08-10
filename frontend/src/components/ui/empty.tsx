import type { ReactNode } from 'react'
import { cn } from '../../lib/cn'

export function Empty({
  title,
  hint,
  action,
  className,
}: {
  title: string
  hint?: string
  action?: ReactNode
  className?: string
}) {
  return (
    <div className={cn('flex flex-col items-center justify-center gap-3 py-14 text-center', className)}>
      <div className="flex h-10 w-10 items-center justify-center rounded-full border border-line-strong bg-elev1 text-ink-4">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
          <path d="M9 18h6M10 21h4M6 3h12a1 1 0 0 1 1 1v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V4a1 1 0 0 1 1-1z" strokeLinecap="round" />
        </svg>
      </div>
      <div className="text-[13px] font-medium text-ink-2">{title}</div>
      {hint && <div className="max-w-[260px] text-[12px] text-ink-4">{hint}</div>}
      {action}
    </div>
  )
}
