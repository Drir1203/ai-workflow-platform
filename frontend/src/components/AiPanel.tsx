import { useState } from 'react'
import { cn } from '../lib/cn'
import { Button } from './ui/button'
import type { DataLayer } from '../lib/view'

interface Msg {
  role: 'user' | 'assistant'
  text: string
}

const WELCOME: Msg = {
  role: 'assistant',
  text: '我是工作区 AI 助手。可以问我项目进度、任务待办或部署状态。',
}

export function AiPanel({ layer }: { layer: DataLayer }) {
  const [open, setOpen] = useState(false)
  const [msgs, setMsgs] = useState<Msg[]>([WELCOME])
  const [input, setInput] = useState('')
  const [busy, setBusy] = useState(false)

  async function send() {
    const q = input.trim()
    if (!q || busy) return
    setInput('')
    setMsgs((m) => [...m, { role: 'user', text: q }])
    setBusy(true)
    try {
      const { answer } = await layer.chat(q)
      setMsgs((m) => [...m, { role: 'assistant', text: answer }])
    } catch {
      setMsgs((m) => [...m, { role: 'assistant', text: '请求失败，请确认后端已配置 AI 引擎。' }])
    } finally {
      setBusy(false)
    }
  }

  return (
    <>
      <button
        onClick={() => setOpen((o) => !o)}
        aria-label="AI 助手"
        className="fixed bottom-20 right-6 z-40 flex h-12 w-12 items-center justify-center rounded-full bg-gradient-to-br from-gold to-gold-deep text-[#1A1406] shadow-gold transition-transform duration-150 hover:scale-[1.04] active:scale-[.95] md:bottom-6"
      >
        <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
          <path d="M12 2l1.9 5.1L19 9l-5.1 1.9L12 16l-1.9-5.1L5 9l5.1-1.9L12 2zm7 10l1 2.7 2.7 1-2.7 1-1 2.7-1-2.7-2.7-1 2.7-1 1-2.7zM4 13l.9 2.4L7.3 16l-2.4.9L4 19l-.9-2.1L.7 16l2.4-.6L4 13z" />
        </svg>
      </button>

      {open && (
        <div className="glass fixed bottom-40 right-6 z-40 flex h-[440px] max-h-[calc(100dvh-180px)] w-[360px] max-w-[calc(100vw-48px)] flex-col overflow-hidden rounded-card border border-line-soft shadow-modal animate-fadeUp md:bottom-24">
          <div className="flex items-center justify-between border-b border-line bg-elev1 px-4 py-3">
            <div className="flex items-center gap-2 text-[13px] font-semibold text-ink">
              <span className="h-1.5 w-1.5 rounded-full bg-gold" style={{ boxShadow: '0 0 6px rgba(217,164,65,.8)' }} />
              AI 助手
            </div>
            <button
              onClick={() => setOpen(false)}
              className="flex h-6 w-6 items-center justify-center rounded-md text-ink-3 hover:bg-active hover:text-ink"
              aria-label="收起"
            >
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M18 6 6 18M6 6l12 12" strokeLinecap="round" />
              </svg>
            </button>
          </div>

          <div className="flex-1 space-y-3 overflow-y-auto bg-panel/55 p-4">
            {msgs.map((m, i) => (
              <div key={i} className={cn('flex', m.role === 'user' ? 'justify-end' : 'justify-start')}>
                <div
                  className={cn(
                    'max-w-[82%] rounded-lg px-3 py-2 text-[12.5px] leading-relaxed',
                    m.role === 'user'
                      ? 'border border-gold/20 bg-gold-tint text-gold'
                      : 'border border-line-strong bg-elev2 text-ink-2',
                  )}
                >
                  {m.text}
                </div>
              </div>
            ))}
            {busy && (
              <div className="flex gap-1.5 px-1 py-2">
                <span className="h-1.5 w-1.5 animate-pulseDot rounded-full bg-gold" />
                <span className="h-1.5 w-1.5 animate-pulseDot rounded-full bg-gold" style={{ animationDelay: '150ms' }} />
                <span className="h-1.5 w-1.5 animate-pulseDot rounded-full bg-gold" style={{ animationDelay: '300ms' }} />
              </div>
            )}
          </div>

          <div className="flex gap-2 border-t border-line bg-elev1 p-3">
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') send()
              }}
              placeholder="问点什么…"
              className="h-9 flex-1 rounded-lg border border-line-soft bg-bg px-3 text-[13px] text-ink placeholder:text-ink-4 focus:border-gold-primary/60 focus:outline-none focus:ring-2 focus:ring-gold-primary/25"
            />
            <Button size="sm" onClick={send} disabled={busy}>
              发送
            </Button>
          </div>
        </div>
      )}
    </>
  )
}
