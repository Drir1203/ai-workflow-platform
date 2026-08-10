import type { HTMLAttributes } from 'react'
import { cn } from '../../lib/cn'

export type BadgeTone = 'gold' | 'success' | 'warning' | 'error' | 'info' | 'neutral'

const tones: Record<BadgeTone, string> = {
  gold: 'border-gold/25 bg-gold-tint text-gold',
  success: 'border-success/25 bg-success/10 text-success',
  warning: 'border-warning/25 bg-warning/10 text-warning',
  error: 'border-error/25 bg-error/10 text-error',
  info: 'border-info/25 bg-info/10 text-info',
  neutral: 'border-line-strong bg-active text-ink-2',
}

interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  tone?: BadgeTone
  dot?: boolean
}

export function Badge({ tone = 'neutral', dot = true, className, children, ...props }: BadgeProps) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full border px-2 py-0.5 text-[11px] font-medium leading-none',
        tones[tone],
        className,
      )}
      {...props}
    >
      {dot && (
        <span
          className="h-1.5 w-1.5 rounded-full bg-current"
          style={{ boxShadow: '0 0 5px currentColor' }}
        />
      )}
      {children}
    </span>
  )
}
