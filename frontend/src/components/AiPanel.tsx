import { useEffect, useRef, useState } from 'react'
import { cn } from '../lib/cn'
import { Button } from './ui/button'
import type { DataLayer } from '../lib/view'
import type { CopilotEvent, CopilotMessage, CopilotResultKind } from '../types'

// 单条消息 = 若干渲染块：文本增量 / 状态徽章 / 结构化结果 / 错误
interface Block {
  kind: 'text' | 'status' | 'result' | 'error'
  text?: string
  resultKind?: CopilotResultKind
  data?: Record<string, unknown>
}

interface ChatMsg {
  role: 'user' | 'assistant'
  blocks: Block[]
}

const WELCOME: ChatMsg = {
  role: 'assistant',
  blocks: [
    {
      kind: 'text',
      text: '我是「AI 智序」AI 副驾，可以用自然语言直接指挥平台干活。\n试着对我说：\n· 帮我写本周周报\n· 部署流程是什么\n· 创建一个高优任务',
    },
  ],
}

// 折叠成后端 wire 历史：user 取首个文本块；assistant 拼文本 + 结果摘要；最后拼当前输入
function foldHistory(msgs: ChatMsg[], lastUser: string): CopilotMessage[] {
  const out: CopilotMessage[] = []
  for (const m of msgs.slice(-11)) {
    if (m.role === 'user') {
      const first = m.blocks.find((b) => b.kind === 'text')?.text
      if (first) out.push({ role: 'user', content: first })
    } else {
      const parts = m.blocks
        .map((b) => {
          if (b.kind === 'text') return b.text ?? ''
          if (b.kind === 'status') return b.text ?? ''
          if (b.kind === 'result') return String((b.data?.output as string) ?? (b.data?.title as string) ?? '')
          return ''
        })
        .filter(Boolean)
      if (parts.length) out.push({ role: 'assistant', content: parts.join('\n') })
    }
  }
  out.push({ role: 'user', content: lastUser })
  return out
}

export function AiPanel({ layer }: { layer: DataLayer }) {
  const [open, setOpen] = useState(false)
  const [msgs, setMsgs] = useState<ChatMsg[]>([WELCOME])
  const [draft, setDraft] = useState('')
  const [busy, setBusy] = useState(false)
  const listRef = useRef<HTMLDivElement>(null)

  // 新内容 / 忙碌态变化时自动滚到底部
  useEffect(() => {
    const el = listRef.current
    if (el) el.scrollTop = el.scrollHeight
  }, [msgs, busy])

  // 往最后一条 assistant 消息追加一个块
  function pushBlock(block: Block) {
    setMsgs((m) => {
      if (m.length === 0) return m
      const next = [...m]
      const last = next[next.length - 1]
      if (last.role !== 'assistant') return m
      next[next.length - 1] = { ...last, blocks: [...last.blocks, block] }
      return next
    })
  }

  // 分发 SSE 事件到消息块；text 增量合并进末尾文本块
  function applyEvent(ev: CopilotEvent) {
    if (ev.type === 'text') {
      setMsgs((m) => {
        const next = [...m]
        const last = next[next.length - 1]
        if (!last || last.role !== 'assistant') return m
        const blocks = [...last.blocks]
        const tail = blocks[blocks.length - 1]
        if (tail && tail.kind === 'text') {
          blocks[blocks.length - 1] = { ...tail, text: (tail.text ?? '') + ev.delta }
        } else {
          blocks.push({ kind: 'text', text: ev.delta })
        }
        next[next.length - 1] = { ...last, blocks }
        return next
      })
      return
    }
    if (ev.type === 'status') pushBlock({ kind: 'status', text: ev.message })
    else if (ev.type === 'result') pushBlock({ kind: 'result', resultKind: ev.kind, data: ev.data })
    else if (ev.type === 'error') pushBlock({ kind: 'error', text: ev.message })
  }

  async function send() {
    const q = draft.trim()
    if (!q || busy) return
    setDraft('')
    const history = foldHistory(msgs, q)
    setMsgs((m) => [...m, { role: 'user', blocks: [{ kind: 'text', text: q }] }, { role: 'assistant', blocks: [] }])
    setBusy(true)
    try {
      for await (const ev of layer.streamCopilot(history)) {
        applyEvent(ev)
      }
    } catch {
      applyEvent({ type: 'error', code: 'network', message: '请求失败，请确认后端已配置 AI 引擎。' })
    } finally {
      setBusy(false)
    }
  }

  function clearChat() {
    setMsgs([WELCOME])
  }

  function renderBlock(b: Block, i: number) {
    if (b.kind === 'status') {
      return (
        <div key={i} className="my-1 flex items-center gap-1.5 text-[11.5px] text-ink-3">
          <span className="h-1 w-1 shrink-0 rounded-full bg-gold" />
          {b.text}
        </div>
      )
    }
    if (b.kind === 'error') {
      return (
        <div key={i} className="mt-1 rounded-md border border-red-400/30 bg-red-400/10 px-2.5 py-1.5 text-[12px] text-red-300">
          {b.text}
        </div>
      )
    }
    if (b.kind === 'result') {
      const d = b.data ?? {}
      // agent 输出量大：灰底可滚动容器，whitespace-pre-wrap 保留换行
      if (b.resultKind === 'agent') {
        return (
          <div key={i} className="mt-1.5 max-h-52 overflow-y-auto whitespace-pre-wrap rounded-md border border-line-strong bg-bg/70 p-2.5 text-[12px] text-ink-2">
            {String(d.output ?? '')}
          </div>
        )
      }
      const title = String(d.title ?? d.name ?? '完成')
      const sub =
        b.resultKind === 'workflow'
          ? `运行 ID ${String(d.run_id ?? '')}`
          : b.resultKind === 'task'
            ? `项目 ${String(d.project_name ?? d.project_id ?? '')} · ${String(d.priority ?? 'medium')}`
            : b.resultKind === 'project'
              ? `状态 ${String(d.status ?? '')}`
              : b.resultKind === 'knowledge'
                ? `项目 ${String(d.project_name ?? '')} · ${(d.sources as unknown[])?.length ?? 0} 个来源`
                : ''
      return (
        <div key={i} className="mt-1.5 rounded-md border border-gold/25 bg-gold-tint px-2.5 py-1.5 text-[12px] text-gold">
          <div className="font-medium">{title}</div>
          {sub && <div className="mt-0.5 text-[11px] text-ink-3">{sub}</div>}
        </div>
      )
    }
    return (
      <div key={i} className="whitespace-pre-wrap">
        {b.text}
      </div>
    )
  }

  return (
    <>
      <button
        onClick={() => setOpen((o) => !o)}
        aria-label="AI 副驾"
        className="fixed bottom-20 right-6 z-40 flex h-12 w-12 items-center justify-center rounded-full bg-gradient-to-br from-gold to-gold-deep text-[#1A1406] shadow-gold transition-transform duration-150 hover:scale-[1.04] active:scale-[.95] md:bottom-6"
      >
        <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
          <path d="M12 2l1.9 5.1L19 9l-5.1 1.9L12 16l-1.9-5.1L5 9l5.1-1.9L12 2zm7 10l1 2.7 2.7 1-2.7 1-1 2.7-1-2.7-2.7-1 2.7-1 1-2.7zM4 13l.9 2.4L7.3 16l-2.4.9L4 19l-.9-2.1L.7 16l2.4-.6L4 13z" />
        </svg>
      </button>

      {open && (
        <div className="glass fixed bottom-40 right-6 z-40 flex h-[480px] max-h-[calc(100dvh-180px)] w-[360px] max-w-[calc(100vw-48px)] flex-col overflow-hidden rounded-card border border-line-soft shadow-modal animate-fadeUp md:bottom-24">
          <div className="flex items-center justify-between border-b border-line bg-elev1 px-4 py-3">
            <div className="flex items-center gap-2 text-[13px] font-semibold text-ink">
              <span className="h-1.5 w-1.5 rounded-full bg-gold" style={{ boxShadow: '0 0 6px rgba(217,164,65,.8)' }} />
              AI 副驾
            </div>
            <div className="flex items-center gap-1">
              <button
                onClick={clearChat}
                className="rounded-md px-2 py-1 text-[11.5px] text-ink-3 hover:bg-active hover:text-ink"
              >
                清空会话
              </button>
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
          </div>

          <div ref={listRef} className="flex-1 space-y-3 overflow-y-auto bg-panel/55 p-4">
            {msgs.map((m, i) => (
              <div key={i} className={cn('flex', m.role === 'user' ? 'justify-end' : 'justify-start')}>
                <div
                  className={cn(
                    'max-w-[85%] rounded-lg px-3 py-2 text-[12.5px] leading-relaxed',
                    m.role === 'user'
                      ? 'border border-gold/20 bg-gold-tint text-gold'
                      : 'border border-line-strong bg-elev2 text-ink-2',
                  )}
                >
                  {m.blocks.map(renderBlock)}
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
            <textarea
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              onKeyDown={(e) => {
                // Enter 发送 / Shift+Enter 换行
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault()
                  send()
                }
              }}
              rows={2}
              placeholder="用人话指挥平台干活…"
              className="max-h-24 flex-1 resize-none rounded-lg border border-line-soft bg-bg px-3 py-2 text-[13px] leading-snug text-ink placeholder:text-ink-4 focus:border-gold-primary/60 focus:outline-none focus:ring-2 focus:ring-gold-primary/25"
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
