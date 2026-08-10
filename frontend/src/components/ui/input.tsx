import { forwardRef, type InputHTMLAttributes, type TextareaHTMLAttributes } from 'react'
import { cn } from '../../lib/cn'

export const Input = forwardRef<HTMLInputElement, InputHTMLAttributes<HTMLInputElement>>(
  ({ className, ...props }, ref) => (
    <input
      ref={ref}
      className={cn(
        'h-9 w-full rounded-lg border border-line-soft bg-elev1 px-3 text-[13px] text-ink',
        'shadow-inner-light placeholder:text-ink-4',
        'transition-[border-color,box-shadow] duration-150',
        'focus:border-gold-primary/60 focus:outline-none focus:ring-2 focus:ring-gold-primary/25',
        className,
      )}
      {...props}
    />
  ),
)
Input.displayName = 'Input'

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaHTMLAttributes<HTMLTextAreaElement>>(
  ({ className, ...props }, ref) => (
    <textarea
      ref={ref}
      className={cn(
        'w-full rounded-lg border border-line-soft bg-elev1 px-3 py-2 text-[13px] text-ink',
        'shadow-inner-light placeholder:text-ink-4',
        'transition-[border-color,box-shadow] duration-150',
        'focus:border-gold-primary/60 focus:outline-none focus:ring-2 focus:ring-gold-primary/25',
        className,
      )}
      {...props}
    />
  ),
)
Textarea.displayName = 'Textarea'
