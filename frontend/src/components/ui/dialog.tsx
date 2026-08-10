import { useEffect, type ReactNode } from 'react'
import { createPortal } from 'react-dom'
import { cn } from '../../lib/cn'

interface DialogProps {
  open: boolean
  onClose: () => void
  title?: string
  children: ReactNode
  className?: string
}

export function Dialog({ open, onClose, title, children, className }: DialogProps) {
  useEffect(() => {
    if (!open) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open, onClose])

  if (!open) return null
  return createPortal(
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={onClose} />
      <div
        className={cn(
          'glass-panel relative w-full max-w-md rounded-card border border-line-soft shadow-modal',
          'animate-fadeUp',
          className,
        )}
      >
        {title && (
          <div className="flex items-center justify-between border-b border-line px-5 py-4">
            <h3 className="text-[14px] font-semibold text-ink">{title}</h3>
            <button
              onClick={onClose}
              className="flex h-6 w-6 items-center justify-center rounded-md text-ink-3 transition-colors hover:bg-active hover:text-ink"
              aria-label="关闭"
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M18 6 6 18M6 6l12 12" strokeLinecap="round" />
              </svg>
            </button>
          </div>
        )}
        <div className="p-5">{children}</div>
      </div>
    </div>,
    document.body,
  )
}
