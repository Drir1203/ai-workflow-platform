import { forwardRef, type ButtonHTMLAttributes, type ReactNode } from 'react'
import { cn } from '../../lib/cn'

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger'
  size?: 'sm' | 'md' | 'lg'
  loading?: boolean
  children?: ReactNode
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ variant = 'primary', size = 'md', loading, className, children, disabled, ...props }, ref) => {
    return (
      <button
        ref={ref}
        disabled={disabled || loading}
        className={cn(
          'inline-flex select-none items-center justify-center gap-2 rounded-lg font-medium',
          'transition-[transform,background-color,border-color,box-shadow] duration-150 active:scale-[.97]',
          'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-gold-primary/60',
          'disabled:pointer-events-none disabled:opacity-50',
          size === 'sm' && 'h-7 px-2.5 text-[12px]',
          size === 'md' && 'h-9 px-4 text-[13px]',
          size === 'lg' && 'h-11 px-6 text-[14px]',
          variant === 'primary' &&
            'bg-gradient-to-br from-gold to-gold-deep text-[#1A1406] shadow-gold hover:brightness-[1.06]',
          variant === 'secondary' && 'border border-line-strong bg-transparent text-ink hover:bg-active',
          variant === 'ghost' && 'text-ink-2 hover:bg-active hover:text-ink',
          variant === 'danger' && 'border border-error/40 text-error hover:bg-error/10',
          className,
        )}
        {...props}
      >
        {loading && <Spinner className="h-3.5 w-3.5" />}
        {children}
      </button>
    )
  },
)
Button.displayName = 'Button'

export function Spinner({ className }: { className?: string }) {
  return (
    <svg className={cn('animate-spin', className)} viewBox="0 0 24 24" fill="none">
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path className="opacity-90" fill="currentColor" d="M4 12a8 8 0 0 1 8-8V0C5.4 0 0 5.4 0 12h4z" />
    </svg>
  )
}
