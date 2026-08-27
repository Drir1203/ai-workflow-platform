import { useCallback, useEffect, useState } from 'react'
import { DocEditor } from '../components/DocEditor'
import { Button } from '../components/ui/button'
import { Card } from '../components/ui/card'
import { Empty } from '../components/ui/empty'
import type { DataLayer } from '../lib/view'
import type { Doc, Project } from '../types'

export function DocTab({ layer, project }: { layer: DataLayer; project: Project }) {
  const [docs, setDocs] = useState<Doc[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [creating, setCreating] = useState(false)
  const [openId, setOpenId] = useState<string | null>(null)

  const refresh = useCallback(async () => {
    try {
      setDocs(await layer.listDocs(project.id))
      setError('')
    } catch (e) {
      setError(e instanceof Error ? e.message : '加载失败')
    } finally {
      setLoading(false)
    }
  }, [layer, project.id])

  useEffect(() => {
    refresh()
  }, [refresh])

  async function onCreate() {
    if (creating) return
    setCreating(true)
    setError('')
    try {
      const d = await layer.createDoc({ project_id: project.id, title: '未命名文档', content: '' })
      setDocs((prev) => [d, ...prev])
      setOpenId(d.id)
    } catch (e) {
      setError(e instanceof Error ? e.message : '新建失败')
    } finally {
      setCreating(false)
    }
  }

  async function onDelete(d: Doc) {
    if (!window.confirm(`确定删除「${d.title}」？`)) return
    try {
      await layer.deleteDoc(d.id)
      if (openId === d.id) setOpenId(null)
      setDocs((prev) => prev.filter((x) => x.id !== d.id))
    } catch (e) {
      setError(e instanceof Error ? e.message : '删除失败')
    }
  }

  function onSaved(d: Doc) {
    setDocs((prev) => prev.map((x) => (x.id === d.id ? d : x)))
  }

  const open = docs.find((d) => d.id === openId) ?? null

  // 已打开某篇文档：整区切换为编辑器（textarea 需要全高滚动区）
  if (open) {
    return <DocEditor doc={open} layer={layer} onClose={() => setOpenId(null)} onSaved={onSaved} />
  }

  return (
    <div className="space-y-4">
      {error && (
        <div className="rounded-lg border border-error/20 bg-error/10 px-3 py-2 text-[12px] text-error">{error}</div>
      )}
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-[13px] font-semibold text-ink-2">文档</h2>
        <Button size="sm" variant="secondary" loading={creating} onClick={() => void onCreate()}>
          + 新建文档
        </Button>
      </div>
      {loading ? (
        <div className="p-8 text-center text-[12.5px] text-ink-4">加载文档中…</div>
      ) : docs.length === 0 ? (
        <Card>
          <Empty
            title="还没有文档"
            hint="新建一份 Markdown 文档，编辑后可预览渲染，还能让 AI 续写、润色或总结。"
            action={
              <Button size="sm" onClick={() => void onCreate()}>
                新建文档
              </Button>
            }
          />
        </Card>
      ) : (
        <Card className="overflow-hidden">
          <div>
            {docs.map((d) => (
              <div
                key={d.id}
                className="flex flex-wrap items-center gap-3 border-b border-line px-4 py-3 last:border-b-0"
              >
                <button onClick={() => setOpenId(d.id)} className="min-w-0 flex-1 text-left">
                  <div className="truncate text-[13px] font-medium text-ink">{d.title}</div>
                  <div className="mt-0.5 font-mono text-[10.5px] tabular-nums text-ink-5">
                    {new Date(d.updated_at).toLocaleString()}
                  </div>
                </button>
                <button
                  onClick={() => void onDelete(d)}
                  className="text-[11px] text-ink-4 transition-colors hover:text-error"
                >
                  删除
                </button>
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  )
}
