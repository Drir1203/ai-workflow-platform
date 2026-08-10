import { useState } from 'react'
import { cn } from '../lib/cn'
import { applyTheme, getTheme, THEMES, type ThemeId } from '../lib/theme'

export function ThemeSwitcher() {
  const [open, setOpen] = useState(false)
  const [theme, setTheme] = useState<ThemeId>(getTheme())
  const current = THEMES.find((t) => t.id === theme) ?? THEMES[0]

  return (
    <div className="relative">
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex h-8 items-center gap-2 rounded-lg border border-line-strong px-2.5 text-[12px] text-ink-2 transition-colors duration-150 hover:bg-active hover:text-ink focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-gold-primary/60"
        aria-haspopup="menu"
        aria-expanded={open}
      >
        <span
          className="h-3 w-3 rounded-full border border-line-strong"
          style={{ background: current.swatch.bg, boxShadow: `inset 0 0 0 3px ${current.swatch.bg}, inset 0 0 0 4px ${current.swatch.gold}` }}
        />
        <span className="hidden sm:inline">{current.label}</span>
        <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" className={cn('transition-transform duration-150', open && 'rotate-180')}>
          <path d="m6 9 6 6 6-6" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </button>

      {open && (
        <>
          <div className="fixed inset-0 z-40" onClick={() => setOpen(false)} />
          <div className="absolute right-0 top-10 z-50 w-48 overflow-hidden rounded-card border border-line-soft bg-elev2 p-1 shadow-modal animate-fadeUp">
            {THEMES.map((t) => (
              <button
                key={t.id}
                onClick={() => {
                  applyTheme(t.id)
                  setTheme(t.id)
                  setOpen(false)
                }}
                className={cn(
                  'flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-left transition-colors duration-150',
                  t.id === theme ? 'bg-active text-gold' : 'text-ink-2 hover:bg-active/60 hover:text-ink',
                )}
              >
                <span
                  className="h-4 w-4 shrink-0 rounded-full border border-line-strong"
                  style={{ background: t.swatch.bg, boxShadow: `inset 0 0 0 2px ${t.swatch.bg}, inset 0 0 0 3px ${t.swatch.gold}` }}
                />
                <span className="flex flex-col">
                  <span className="text-[12px] font-medium leading-tight">{t.label}</span>
                  <span className="text-[10px] text-ink-5">{t.hint}</span>
                </span>
                {t.id === theme && (
                  <svg className="ml-auto" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4">
                    <path d="M4 12.5 9.5 18 20 6.5" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                )}
              </button>
            ))}
          </div>
        </>
      )}
    </div>
  )
}
