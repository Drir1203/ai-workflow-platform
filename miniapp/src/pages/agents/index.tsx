import { useEffect, useMemo, useRef, useState } from 'react'
import { Input, Picker, ScrollView, Text, Textarea, View } from '@tarojs/components'
import Taro, { useDidShow } from '@tarojs/taro'
import { api } from '../../api/client'
import { BASE } from '../../api/config'
import type { AgentInfo, AgentRun, Project } from '../../types'

const STATUS_COLOR: Record<string, string> = {
  succeeded: '#7FD1A0',
  failed: '#E0694C',
  running: '#E5B567',
  pending: '#8FA8C0',
}

const STATUS_LABEL: Record<string, string> = {
  pending: '排队中',
  running: '执行中',
  succeeded: '成功',
  failed: '失败',
}

function StatusPill({ status }: { status: string }) {
  const color = STATUS_COLOR[status] || '#8FA8C0'
  return (
    <View
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: '8rpx',
        padding: '4rpx 16rpx',
        borderRadius: '999rpx',
        background: 'rgba(255,255,255,0.06)',
        border: '1rpx solid rgba(255,255,255,0.1)',
      }}
    >
      <View style={{ width: '10rpx', height: '10rpx', borderRadius: '50%', background: color, boxShadow: `0 0 8rpx ${color}66` }} />
      <Text style={{ fontSize: '22rpx', color }}>{STATUS_LABEL[status] || status}</Text>
    </View>
  )
}

export default function Agents() {
  const [agents, setAgents] = useState<AgentInfo[]>([])
  const [projects, setProjects] = useState<Project[]>([])
  const [runs, setRuns] = useState<AgentRun[]>([])
  const [loading, setLoading] = useState(true)
  const [target, setTarget] = useState<AgentInfo | null>(null)
  const [form, setForm] = useState<Record<string, string>>({})
  const [busy, setBusy] = useState(false)
  const [result, setResult] = useState<AgentRun | null>(null)
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const load = async () => {
    try {
      const [a, p] = await Promise.all([api.listAgents(), api.listProjects()])
      setAgents(a)
      setProjects(p)
    } catch (e: any) {
      Taro.showToast({ title: e.message || '加载失败', icon: 'none' })
    } finally {
      setLoading(false)
    }
  }

  const loadRuns = async () => {
    try {
      const res = await Taro.request({
        url: `${BASE}/api/agents/runs?page_size=10`,
        header: { Authorization: `Bearer ${Taro.getStorageSync('ph_token') || ''}` },
      })
      if (res.statusCode === 200) setRuns((res.data as { items: AgentRun[] }).items || [])
    } catch {
      /* 忽略运行记录加载失败 */
    }
  }

  useDidShow(() => {
    load()
    loadRuns()
  })

  useEffect(() => {
    return () => {
      if (timerRef.current) clearInterval(timerRef.current)
    }
  }, [])

  const openSheet = (agent: AgentInfo) => {
    const initial: Record<string, string> = {}
    for (const p of agent.param_schema) {
      const d = p.default
      initial[p.name] = d === null || d === undefined ? '' : String(d)
    }
    setForm(initial)
    setResult(null)
    setTarget(agent)
  }

  const setField = (name: string, value: string) => setForm((f) => ({ ...f, [name]: value }))

  function startRun() {
    if (!target || busy) return
    setBusy(true)
    setResult(null)
    const params: Record<string, unknown> = {}
    for (const p of target.param_schema) {
      const raw = form[p.name] ?? ''
      if (p.type === 'number') {
        if (raw !== '') params[p.name] = Number(raw)
      } else if (raw !== '') {
        params[p.name] = raw
      }
    }
    const projectId = (params.project_id as string) || undefined
    api
      .runAgent(target.key, { params, project_id: projectId })
      .then((created) => {
        if (timerRef.current) clearInterval(timerRef.current)
        timerRef.current = setInterval(async () => {
          try {
            const run = await api.getAgentRun(created.run_id)
            if (run.status === 'succeeded' || run.status === 'failed') {
              if (timerRef.current) clearInterval(timerRef.current)
              setResult(run)
              setBusy(false)
              if (run.status === 'failed') {
                Taro.showToast({ title: run.error || '运行失败', icon: 'none' })
              }
              loadRuns()
            }
          } catch (e: any) {
            if (timerRef.current) clearInterval(timerRef.current)
            setBusy(false)
            Taro.showToast({ title: e.message || '轮询失败', icon: 'none' })
          }
        }, 1500)
      })
      .catch((e: any) => {
        setBusy(false)
        Taro.showToast({ title: e.message || '运行失败', icon: 'none' })
      })
  }

  const agentName = (key: string) => agents.find((a) => a.key === key)?.name || key

  const runningCount = useMemo(
    () => runs.filter((r) => r.status === 'pending' || r.status === 'running').length,
    [runs],
  )

  return (
    <View style={{ padding: '28rpx', paddingBottom: '80rpx' }}>
      <View style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between', marginBottom: '28rpx' }}>
        <View>
          <Text style={{ fontSize: '40rpx', fontWeight: 650, color: 'var(--ink)' }}>智能体</Text>
          <Text style={{ fontSize: '24rpx', color: 'var(--ink-3)', marginTop: '6rpx', display: 'block' }}>
            预置 AI 智能体 · 异步运行
          </Text>
        </View>
        {runs.length > 0 && (
          <Text style={{ fontSize: '22rpx', color: 'var(--ink-4)' }}>
            {runs.length} 次{runningCount > 0 ? ` · ${runningCount} 进行中` : ''}
          </Text>
        )}
      </View>

      {loading ? (
        <Text style={{ color: 'var(--ink-4)', fontSize: '26rpx' }}>加载中…</Text>
      ) : (
        <ScrollView scrollY style={{ display: 'flex', flexDirection: 'column', gap: '20rpx' }}>
          {agents.map((agent, i) => (
            <View
              key={agent.key}
              className="card"
              style={{ padding: '28rpx', display: 'flex', flexDirection: 'column', gap: '16rpx' }}
              onClick={() => openSheet(agent)}
            >
              <View style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between' }}>
                <Text style={{ fontSize: '30rpx', fontWeight: 600, color: 'var(--ink)' }}>{agent.name}</Text>
                <Text style={{ fontSize: '22rpx', color: 'var(--ink-5)', fontFamily: 'monospace' }}>{agent.key}</Text>
              </View>
              <Text style={{ fontSize: '24rpx', color: 'var(--ink-3)', lineHeight: 1.5, minHeight: '72rpx' }}>
                {agent.description}
              </Text>
              <View style={{ display: 'flex', flexWrap: 'wrap', gap: '12rpx' }}>
                {agent.param_schema.map((p) => (
                  <View
                    key={p.name}
                    style={{
                      padding: '4rpx 16rpx',
                      borderRadius: '999rpx',
                      background: 'var(--bg-elev-1)',
                      border: '1rpx solid var(--border-soft)',
                      fontSize: '20rpx',
                      color: 'var(--ink-4)',
                      fontFamily: 'monospace',
                    }}
                  >
                    {p.name}
                    {p.required ? <Text style={{ color: 'var(--gold)' }}>*</Text> : ''}
                  </View>
                ))}
              </View>
              <View
                className="btn-gold"
                style={{ height: '76rpx', lineHeight: '76rpx', fontSize: '26rpx', marginTop: '4rpx' }}
                onClick={(e) => {
                  e.stopPropagation()
                  openSheet(agent)
                }}
              >
                运行
              </View>
            </View>
          ))}
        </ScrollView>
      )}

      {/* 运行记录 */}
      <Text style={{ fontSize: '28rpx', fontWeight: 600, color: 'var(--ink-2)', marginTop: '36rpx', display: 'block' }}>
        运行记录 <Text style={{ fontSize: '22rpx', color: 'var(--ink-5)' }}>{runs.length}</Text>
      </Text>
      <View style={{ display: 'flex', flexDirection: 'column', gap: '16rpx', marginTop: '16rpx' }}>
        {runs.length === 0 ? (
          <Text style={{ color: 'var(--ink-4)', fontSize: '24rpx' }}>还没有运行记录</Text>
        ) : (
          runs.slice(0, 10).map((run) => (
            <View key={run.id} className="card" style={{ padding: '20rpx 24rpx', display: 'flex', alignItems: 'center', gap: '16rpx' }}>
              <StatusPill status={run.status} />
              <Text style={{ fontSize: '26rpx', color: 'var(--ink)', fontWeight: 500 }}>{agentName(run.agent_key)}</Text>
              {run.project_id ? (
                <Text style={{ fontSize: '22rpx', color: 'var(--ink-4)' }}>
                  {projects.find((p) => p.id === run.project_id)?.name || run.project_id}
                </Text>
              ) : null}
              <Text style={{ fontSize: '20rpx', color: 'var(--ink-5)', marginLeft: 'auto' }}>
                {run.created_at ? new Date(run.created_at).toLocaleString() : ''}
              </Text>
            </View>
          ))
        )}
      </View>

      {/* 运行弹层 */}
      {target && (
        <View style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, zIndex: 999, background: 'rgba(0,0,0,0.62)' }} onClick={() => setTarget(null)}>
          <View
            style={{
              position: 'absolute',
              bottom: 0,
              left: 0,
              right: 0,
              background: 'var(--bg-elev-2)',
              borderTopLeftRadius: '32rpx',
              borderTopRightRadius: '32rpx',
              padding: '32rpx',
              maxHeight: '80vh',
              display: 'flex',
              flexDirection: 'column',
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <Text style={{ fontSize: '32rpx', fontWeight: 600, color: 'var(--ink)', marginBottom: '24rpx' }}>
              运行 · {target.name}
            </Text>

            <ScrollView scrollY style={{ flex: 1, minHeight: 0 }}>
              {target.param_schema.map((p) => (
                <View key={p.name} style={{ marginBottom: '20rpx' }}>
                  <Text style={{ fontSize: '24rpx', color: 'var(--ink-3)', display: 'block', marginBottom: '12rpx' }}>
                    {p.label}
                    {p.required ? <Text style={{ color: 'var(--gold)' }}> *</Text> : ''}
                  </Text>

                  {p.type === 'project_id' ? (
                    (() => {
                      const labels = ['全部项目', ...projects.map((pr) => pr.name)]
                      const values = ['', ...projects.map((pr) => pr.id)]
                      const idx = Math.max(0, values.indexOf(form[p.name] ?? ''))
                      return (
                        <Picker
                          mode="selector"
                          range={labels}
                          value={idx}
                          onChange={(e) => setField(p.name, values[Number(e.detail.value)] ?? '')}
                        >
                          <View className="picker-field" style={{ height: '88rpx', lineHeight: '88rpx', fontSize: '28rpx' }}>
                            {labels[idx]}
                          </View>
                        </Picker>
                      )
                    })()
                  ) : p.type === 'select' ? (
                    (() => {
                      const labels = p.options.map((o) => o.label)
                      const values = p.options.map((o) => o.value)
                      const idx = Math.max(0, values.indexOf(form[p.name] ?? ''))
                      return (
                        <Picker
                          mode="selector"
                          range={labels}
                          value={idx}
                          onChange={(e) => setField(p.name, values[Number(e.detail.value)] ?? '')}
                        >
                          <View className="picker-field" style={{ height: '88rpx', lineHeight: '88rpx', fontSize: '28rpx' }}>
                            {labels[idx] ?? '请选择'}
                          </View>
                        </Picker>
                      )
                    })()
                  ) : p.type === 'textarea' ? (
                    <Textarea
                      value={form[p.name] ?? ''}
                      onInput={(e) => setField(p.name, e.detail.value)}
                      placeholder={p.placeholder}
                      placeholderStyle="color:#6E6C64"
                      style={{
                        width: '100%',
                        background: 'var(--bg-elev-1)',
                        border: '1rpx solid var(--border-soft)',
                        borderRadius: '16rpx',
                        padding: '20rpx 24rpx',
                        fontSize: '26rpx',
                        color: 'var(--ink)',
                        minHeight: '120rpx',
                      }}
                    />
                  ) : (
                    <Input
                      value={form[p.name] ?? ''}
                      type={p.type === 'number' ? 'number' : 'text'}
                      onInput={(e) => setField(p.name, e.detail.value)}
                      placeholder={p.placeholder}
                      placeholderStyle="color:#6E6C64"
                      style={{
                        height: '88rpx',
                        background: 'var(--bg-elev-1)',
                        border: '1rpx solid var(--border-soft)',
                        borderRadius: '16rpx',
                        padding: '0 24rpx',
                        fontSize: '28rpx',
                        color: 'var(--ink)',
                      }}
                    />
                  )}
                </View>
              ))}

              {busy && (
                <Text style={{ fontSize: '24rpx', color: 'var(--ink-4)', marginBottom: '16rpx', display: 'block' }}>
                  执行中，请稍候…
                </Text>
              )}

              {result && (
                <View
                  style={{
                    background: 'var(--bg-elev-1)',
                    border: '1rpx solid var(--border-soft)',
                    borderRadius: '16rpx',
                    padding: '20rpx',
                    marginBottom: '16rpx',
                  }}
                >
                  <View style={{ marginBottom: '12rpx' }}>
                    <StatusPill status={result.status} />
                  </View>
                  {result.status === 'failed' ? (
                    <Text style={{ fontSize: '24rpx', color: '#E0694C', whiteSpace: 'pre-wrap', lineHeight: 1.5 }}>
                      {result.error}
                    </Text>
                  ) : (
                    <Text style={{ fontSize: '24rpx', color: 'var(--ink-2)', whiteSpace: 'pre-wrap', lineHeight: 1.6 }}>
                      {result.output}
                    </Text>
                  )}
                </View>
              )}
            </ScrollView>

            <View
              className="btn-gold"
              style={{ height: '84rpx', lineHeight: '84rpx', fontSize: '28rpx', marginTop: '24rpx' }}
              onClick={() => startRun()}
            >
              运行
            </View>
          </View>
        </View>
      )}
    </View>
  )
}
