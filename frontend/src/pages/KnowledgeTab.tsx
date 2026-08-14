import { useCallback, useEffect, useRef, useState } from 'react'
import { Badge } from '../components/ui/badge'
import { Button } from '../components/ui/button'
import { Card } from '../components/ui/card'
import { Empty } from '../components/ui/empty'
import { Textarea } from '../components/ui/input'
import type { DataLayer } from '../lib/view'
import type { KnowledgeDocument, KnowledgeResponse, Project } from '../types'

const CONTENT_TYPE_LABEL: Record<string, string> = {
  md: 'Markdown',
  txt: 'TXT',
  pdf: 'PDF',
  docx: 'Word',
}

function docStatusTone(status: string): 'success' | 'error' | 'info' {
  return status === 'ready' ? 'success' : status === 'error' ? 'error' : 'info'
}

function docStatusLabel(status: string): string {
  return status === 'ready' ? '就绪' : status === 'error' ? '失败' : '处理中'
}

export function KnowledgeTab({ layer, project }: { layer: DataLayer; project: Project }) {
  const [docs, setDocs] = useState<KnowledgeDocument[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [uploading, setUploading] = useState(false)
  const [scanning, setScanning] = useState(false)
  const [scanMsg, setScanMsg] = useState('')
  const fileRef = useRef<HTMLInputElement>(null)
  const [query, setQuery] = useState('')
  const [asking, setAsking] = useState(false)
  const [result, setResult] = useState<KnowledgeResponse | null>(null)

  const refresh = useCallback(async () => {
    try {
      setDocs(await layer.listDocuments(project.id))
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

  async function onUploadFile(f: File | undefined) {
    if (!f || uploading) return
    if (!/\.(md|txt|pdf|docx)$/i.test(f.name)) {
      setError('不支持的文档格式，仅支持 md/txt/pdf/docx')
      return
    }
    setUploading(true)
    setScanMsg('')
    setError('')
    try {
      await layer.uploadDocument(project.id, f)
      await refresh()
    } catch (e) {
      setError(e instanceof Error ? e.message : '上传失败')
    } finally {
      setUploading(false)
    }
  }

  async function onScan() {
    if (scanning) return
    setScanning(true)
    setScanMsg('')
    try {
      const r = await layer.scanDocuments(project.id)
      setScanMsg(`扫描完成：导入 ${r.imported} 个，跳过 ${r.skipped.length} 个`)
      await refresh()
    } catch (e) {
      setError(e instanceof Error ? e.message : '扫描失败')
    } finally {
      setScanning(false)
    }
  }

  async function onDelete(doc: KnowledgeDocument) {
    if (!window.confirm(`确定删除「${doc.name}」？其切片将一并删除。`)) return
    try {
      setScanMsg('')
      await layer.deleteDocument(project.id, doc.id)
      await refresh()
    } catch (e) {
      setError(e instanceof Error ? e.message : '删除失败')
    }
  }

  async function onAsk(e: { preventDefault: () => void }) {
    e.preventDefault()
    const q = query.trim()
    if (!q || asking) return
    setAsking(true)
    setResult(null)
    try {
      setResult(await layer.queryKnowledge(project.id, q))
      setError('')
    } catch (err) {
      setError(err instanceof Error ? err.message : '提问失败')
    } finally {
      setAsking(false)
    }
  }

  return (
    <div className="grid gap-6 lg:grid-cols-7">
      {error && (
        <div className="col-span-full border-b border-error/20 bg-error/10 px-5 py-1.5 text-[11px] text-error">
          {error}
        </div>
      )}

      <section className="lg:col-span-4">
        <Card className="overflow-hidden">
          <div className="flex flex-wrap items-center justify-between gap-2 border-b border-line px-4 py-3">
            <h2 className="text-[13px] font-semibold text-ink-2">文档库</h2>
            <div className="flex gap-2">
              <input
                ref={fileRef}
                type="file"
                accept=".md,.txt,.pdf,.docx"
                className="hidden"
                onChange={(e) => {
                  void onUploadFile(e.target.files?.[0])
                  e.target.value = ''
                }}
              />
              <Button size="sm" variant="secondary" loading={uploading} onClick={() => fileRef.current?.click()}>
                上传文档
              </Button>
              <Button
                size="sm"
                variant="secondary"
                loading={scanning}
                disabled={!project.local_path}
                onClick={() => void onScan()}
                title={project.local_path ? '扫描项目本地目录自动导入' : '项目未配置 local_path，无法扫描'}
              >
                扫描目录
              </Button>
            </div>
          </div>
          {scanMsg && (
            <div className="border-b border-success/20 bg-success/10 px-4 py-1.5 text-[11px] text-success">
              {scanMsg}
            </div>
          )}
          {loading ? (
            <div className="p-8 text-center text-[12.5px] text-ink-4">加载文档中…</div>
          ) : docs.length === 0 ? (
            <Empty
              title="还没有文档"
              hint="上传 md/txt/pdf/docx，或为项目配置 local_path 后一键扫描项目文档目录。"
            />
          ) : (
            <div className="divide-y divide-line">
              {docs.map((d) => (
                <div key={d.id} className="flex flex-wrap items-center gap-3 px-4 py-3">
                  <Badge tone={docStatusTone(d.status)}>{docStatusLabel(d.status)}</Badge>
                  <span className="text-[13px] font-medium text-ink">{d.name}</span>
                  <span className="rounded border border-line-soft bg-elev1 px-1.5 py-0.5 font-mono text-[10.5px] text-ink-4">
                    {CONTENT_TYPE_LABEL[d.content_type] ?? d.content_type}
                  </span>
                  {d.source === 'scan' && <span className="text-[10.5px] text-ink-5">目录扫描</span>}
                  <span className="ml-auto font-mono text-[10.5px] tabular-nums text-ink-5">
                    {new Date(d.created_at).toLocaleDateString()}
                  </span>
                  <button
                    onClick={() => void onDelete(d)}
                    className="text-[11px] text-ink-4 transition-colors hover:text-error"
                  >
                    删除
                  </button>
                </div>
              ))}
            </div>
          )}
        </Card>
      </section>

      <section className="lg:col-span-3">
        <Card className="space-y-3 p-4">
          <h2 className="text-[13px] font-semibold text-ink-2">知识问答</h2>
          <p className="text-[11.5px] leading-relaxed text-ink-4">
            基于本项目的文档库检索，回答自动附带引用来源。
          </p>
          <form onSubmit={onAsk} className="flex flex-col gap-2">
            <Textarea
              rows={2}
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="如：部署流程是什么？"
            />
            <Button size="sm" type="submit" loading={asking} disabled={!query.trim()}>
              提问
            </Button>
          </form>
          {result && (
            <div className="flex flex-col gap-3 pt-1">
              <div className="rounded-lg border border-line-soft bg-elev1 p-3">
                <div className="whitespace-pre-wrap text-[12px] leading-relaxed text-ink-2">{result.answer}</div>
              </div>
              {result.sources.length > 0 && (
                <div className="flex flex-col gap-2">
                  <div className="text-[11px] font-medium text-ink-4">引用来源</div>
                  {result.sources.map((s) => (
                    <div key={`${s.document_id}-${s.seq}`} className="rounded-lg border border-line-soft bg-elev1 p-2.5">
                      <div className="flex items-center gap-2">
                        <span className="text-[11.5px] font-medium text-gold">{s.document_name}</span>
                        <span className="font-mono text-[10px] text-ink-5">#{s.seq}</span>
                      </div>
                      <div className="mt-1 line-clamp-3 text-[11.5px] leading-relaxed text-ink-3">{s.content}</div>
                      {s.matched.length > 0 && (
                        <div className="mt-1.5 flex flex-wrap gap-1">
                          {s.matched.map((m, mi) => (
                            <span
                              key={`${s.document_id}-${s.seq}-${mi}`}
                              className="rounded border border-gold/25 bg-gold-tint px-1.5 py-0.5 font-mono text-[10px] text-gold"
                            >
                              {m}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </Card>
      </section>
    </div>
  )
}
