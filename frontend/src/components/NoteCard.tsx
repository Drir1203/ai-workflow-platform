import { useState } from 'react'
import { Button } from './ui/button'
import { Textarea } from './ui/input'
import type { Note } from '../types'

export function NoteCard({
  note,
  onUpdate,
  onDelete,
}: {
  note: Note
  onUpdate: (id: string, patch: Partial<Note>) => void
  onDelete: () => void
}) {
  const [editing, setEditing] = useState(false)
  const [content, setContent] = useState(note.content)

  const save = () => {
    onUpdate(note.id, { content })
    setEditing(false)
  }

  return (
    <div className="group rounded-lg border border-line-strong bg-elev2 p-3 shadow-card">
      <div className="flex items-start justify-between gap-2">
        <h4 className="min-w-0 truncate text-[12.5px] font-semibold text-ink">{note.title}</h4>
        <div className="flex shrink-0 items-center gap-1 opacity-0 transition-opacity group-hover:opacity-100">
          <button
            onClick={() => setEditing((e) => !e)}
            className="flex h-6 w-6 items-center justify-center rounded-md text-ink-5 hover:bg-active hover:text-ink"
            aria-label="编辑"
          >
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M12 20h9M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4Z" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </button>
          <button
            onClick={onDelete}
            className="flex h-6 w-6 items-center justify-center rounded-md text-ink-5 hover:bg-error/10 hover:text-error"
            aria-label="删除笔记"
          >
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M18 6 6 18M6 6l12 12" strokeLinecap="round" />
            </svg>
          </button>
        </div>
      </div>
      {editing ? (
        <div className="mt-2 flex flex-col gap-2">
          <Textarea rows={3} value={content} onChange={(e) => setContent(e.target.value)} className="text-[12px]" autoFocus />
          <div className="flex gap-2">
            <Button size="sm" onClick={save}>保存</Button>
            <Button size="sm" variant="ghost" onClick={() => setEditing(false)}>取消</Button>
          </div>
        </div>
      ) : (
        <p className="mt-1.5 text-[12px] leading-relaxed text-ink-3">
          {note.content || <span className="text-ink-5">（空白笔记）</span>}
        </p>
      )}
      <div className="mt-2 font-mono text-[10px] tabular-nums text-ink-5">
        {note.updated_at.slice(0, 16).replace('T', ' ')}
      </div>
    </div>
  )
}
