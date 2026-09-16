import { useEffect, useRef, useState } from 'react'
import { cn } from '../lib/cn'
import type { DataLayer } from '../lib/view'
import { Button } from '../components/ui/button'
import { Input, Textarea } from '../components/ui/input'
import { Markdown } from '../components/ui/markdown'
import type { Doc, WritingOperation } from '../types'

export function DocEditor({
  doc,
  layer,
  onClose,
  onSaved,
}: {
  doc: Doc
  layer: DataLayer
  onClose: () => void
  onSaved: (d: Doc) => void
}) {
  const [title, setTitle] = useState(doc.title)
  const [content, setContent] = useState(doc.content)
  const [mode, setMode] = useState<'edit' | 'preview'>('edit')
  const [saving, setSaving] = useState(false)
  const [writing, setWriting] = useState(false)
  const [error, setError] = useState('')
  const [dirty, setDirty] = useState(false)

  const taRef = useRef<HTMLTextAreaElement>(null)
  // AI 操作快照：记录替换区 [start,end) 的原文，流式错误 / 手动撤销时恢复
  const undoRef = useRef<{ start: number; end: number; text: string } | null>(null)
  // 流式累积 buf：撤销 / 回滚时用其长度定位已插入的区间
  const bufRef = useRef('')

  useEffect(() => {
    setDirty(title !== doc.title || content !== doc.content)
  }, [title, content, doc.title, doc.content])

  // 返回：有未保存改动先确认
  function requestClose() {
    if (dirty && !window.confirm('文档有未保存的改动，确定离开吗？')) return
    onClose()
  }

  async function save() {
    if (saving) return
    setSaving(true)
    setError('')
    try {
      const updated = await layer.updateDoc(doc.id, { title: title.trim() || '未命名文档', content })
      onSaved(updated)
    } catch (e) {
      setError(e instanceof Error ? e.message : '保存失败')
    } finally {
      setSaving(false)
    }
  }

  // 撤销 / 回滚：buf 已插入 [start, start+bufLen)，恢复该区间为快照原文
  function rollback() {
    const s = undoRef.current
    if (!s) return
    const len = bufRef.current.length
    setContent((prev) => prev.slice(0, s.start) + s.text + prev.slice(s.start + len))
    undoRef.current = null
    bufRef.current = ''
  }

  async function runWriting(op: WritingOperation) {
    if (writing) return
    const ta = taRef.current
    let start = ta ? ta.selectionStart : content.length
    let end = ta ? ta.selectionEnd : content.length
    // 无选区：续写/总结追加到文末，润色整篇替换
    if (start === end) {
      if (op === 'polish') {
        start = 0
        end = content.length
      } else {
        start = content.length
        end = content.length
      }
    }
    const target = content.slice(start, end) || content
    undoRef.current = { start, end, text: content.slice(start, end) }
    bufRef.current = ''
    setWriting(true)
    setError('')
    try {
      for await (const ev of layer.streamWriting(op, target)) {
        if (ev.type === 'text') {
          bufRef.current += ev.delta
          const buf = bufRef.current
          setContent((prev) => prev.slice(0, start) + buf + prev.slice(end))
        } else if (ev.type === 'error') {
          setError(ev.message)
          rollback()
          break
        }
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'AI 写作失败')
      rollback()
    } finally {
      setWriting(false)
    }
  }

  return (
    <div className="flex h-full flex-col gap-4">
      <div className="flex flex-wrap items-center gap-2">
        <button
          onClick={requestClose}
          className="flex items-center gap-1.5 text-[12.5px] text-ink-3 transition-colors hover:text-gold"
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M19 12H5m7-7-7 7 7 7" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
          返回文档列表
        </button>
        <div className="flex-1" />
        <div className="flex overflow-hidden rounded-lg border border-line-soft">
          {(['edit', 'preview'] as const).map((m) => (
            <button
              key={m}
              onClick={() => setMode(m)}
              className={cn(
                'px-3 py-1.5 text-[12px] transition-colors',
                mode === m ? 'bg-gold-tint-bg text-gold' : 'text-ink-3 hover:text-ink',
              )}
            >
              {m === 'edit' ? '编辑' : '预览'}
            </button>
          ))}
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <Input
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="文档标题"
          className="max-w-xs flex-1"
        />
        <Button size="sm" variant="secondary" disabled={writing} onClick={() => void runWriting('continue')}>
          续写
        </Button>
        <Button size="sm" variant="secondary" disabled={writing} onClick={() => void runWriting('polish')}>
          润色
        </Button>
        <Button size="sm" variant="secondary" disabled={writing} onClick={() => void runWriting('summarize')}>
          总结
        </Button>
        {dirty && <span className="h-2 w-2 shrink-0 rounded-full bg-gold-primary" title="有未保存改动" />}
        <Button size="sm" onClick={() => void save()} loading={saving} disabled={!dirty || writing}>
          保存
        </Button>
        {undoRef.current && !writing && (
          <Button size="sm" variant="ghost" onClick={rollback}>
            撤销
          </Button>
        )}
      </div>

      {writing && (
        <div className="flex items-center gap-2 text-[12px] text-gold">
          <span className="h-3 w-3 animate-spin rounded-full border-2 border-gold-primary/40 border-t-gold-primary" />
          AI 正在生成，结果将流式写入（可撤销）
        </div>
      )}
      {error && (
        <div className="rounded-lg border border-error/20 bg-error/10 px-3 py-2 text-[12px] text-error">{error}</div>
      )}

      {mode === 'edit' ? (
        <Textarea
          ref={taRef}
          value={content}
          onChange={(e) => {
            // 手动编辑使 AI 快照失效，撤销按钮随之隐藏
            undoRef.current = null
            bufRef.current = ''
            setContent(e.target.value)
          }}
          className="min-h-[360px] flex-1 resize-y font-mono text-[12.5px] leading-relaxed"
          placeholder="在此输入 Markdown 内容…（# 标题、- 列表、表格、```代码块 均可预览渲染）"
        />
      ) : (
        <div className="min-h-[360px] flex-1 overflow-y-auto rounded-xl border border-line-soft bg-elev1 p-5">
          {content.trim() ? (
            <Markdown>{content}</Markdown>
          ) : (
            <p className="text-[12px] text-ink-5">暂无内容</p>
          )}
        </div>
      )}
    </div>
  )
}
