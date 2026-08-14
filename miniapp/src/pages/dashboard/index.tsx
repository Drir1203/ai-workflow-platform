import { useCallback, useMemo, useState } from 'react'
import { Input, ScrollView, Text, View } from '@tarojs/components'
import Taro, { useDidShow } from '@tarojs/taro'
import { api, clearSession, getSessionUser } from '../../api/client'
import AiSheet from '../../components/AiSheet'
import ProjectCard from '../../components/ProjectCard'
import StatCard from '../../components/StatCard'
import type { Note, Project, Task } from '../../types'

export default function Dashboard() {
  const [projects, setProjects] = useState<Project[]>([])
  const [tasks, setTasks] = useState<Task[]>([])
  const [notes, setNotes] = useState<Note[]>([])
  const [loading, setLoading] = useState(true)
  const [showNew, setShowNew] = useState(false)
  const [newName, setNewName] = useState('')
  const [newDesc, setNewDesc] = useState('')
  const [aiOpen, setAiOpen] = useState(false)
  const user = getSessionUser()

  const load = useCallback(async () => {
    try {
      const [p, t, n] = await Promise.all([api.listProjects(), api.listTasks(), api.listNotes()])
      setProjects(p)
      setTasks(t)
      setNotes(n)
    } catch (e: any) {
      Taro.showToast({ title: e.message || '加载失败', icon: 'none' })
    } finally {
      setLoading(false)
    }
  }, [])

  useDidShow(() => {
    load()
    // 触发订阅消息到期提醒（服务端发送后一次性）
    api.sendReminders().catch(() => {})
  })

  const stats = useMemo(() => {
    const total = tasks.length
    const done = tasks.filter((t) => t.status === 'done').length
    const inProgress = tasks.filter((t) => t.status === 'in_progress').length
    const rate = total ? Math.round((done / total) * 1000) / 10 : 0
    return {
      active: projects.filter((p) => p.status === 'active').length,
      inProgress,
      rate,
      total,
      done,
    }
  }, [tasks, projects])

  async function createProject() {
    if (!newName.trim()) return
    try {
      await api.createProject({ name: newName.trim(), description: newDesc.trim() || undefined })
      setNewName('')
      setNewDesc('')
      setShowNew(false)
      load()
    } catch (e: any) {
      Taro.showToast({ title: e.message || '创建失败', icon: 'none' })
    }
  }

  function openProject(id: string) {
    Taro.navigateTo({ url: `/pages/project/index?id=${id}` })
  }

  function logout() {
    Taro.showModal({
      title: '退出登录',
      content: '确定退出当前账号？',
      success: (res) => {
        if (res.confirm) {
          clearSession()
          Taro.reLaunch({ url: '/pages/login/index' })
        }
      },
    })
  }

  return (
    <View style={{ padding: '28rpx', paddingBottom: '160rpx' }}>
      <View style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '28rpx' }}>
        <View>
          <Text style={{ fontSize: '40rpx', fontWeight: 650, color: 'var(--ink)' }}>工作台</Text>
          <Text style={{ fontSize: '24rpx', color: 'var(--ink-3)', marginTop: '6rpx', display: 'block' }}>
            {user ? `${user.name}，管理你的项目与任务` : '管理你的项目与任务'}
          </Text>
        </View>
        <View style={{ display: 'flex', gap: '16rpx' }}>
          <Text onClick={() => Taro.navigateTo({ url: '/pages/agents/index' })} style={{ fontSize: '24rpx', color: 'var(--gold)', padding: '12rpx 24rpx', border: '1rpx solid rgba(217,164,65,0.4)', borderRadius: '14rpx' }}>
            智能体
          </Text>
          <Text onClick={() => setShowNew(true)} style={{ fontSize: '24rpx', color: 'var(--ink-3)', padding: '12rpx 24rpx', border: '1rpx solid var(--border-soft)', borderRadius: '14rpx' }}>
            + 新建
          </Text>
          <Text onClick={logout} style={{ fontSize: '24rpx', color: 'var(--ink-3)', padding: '12rpx' }}>
            退出
          </Text>
        </View>
      </View>

      <View style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20rpx', marginBottom: '32rpx' }}>
        <StatCard label="活跃项目" value={stats.active} sub={`${projects.length} 个全部`} />
        <StatCard label="进行中任务" value={stats.inProgress} sub={`${stats.total} 个总计`} />
        <StatCard label="完成率" value={`${stats.rate}%`} sub={`${stats.done} / ${stats.total} 已完成`} />
        <StatCard label="笔记" value={notes.length} sub="工作区" />
      </View>

      <Text style={{ fontSize: '28rpx', fontWeight: 600, color: 'var(--ink-2)', marginBottom: '20rpx', display: 'block' }}>
        项目 <Text className="num" style={{ fontSize: '24rpx' }}>{projects.length}</Text>
      </Text>

      {loading ? (
        <Text style={{ color: 'var(--ink-4)', fontSize: '26rpx' }}>加载中…</Text>
      ) : projects.length === 0 ? (
        <View className="card" style={{ padding: '60rpx 28rpx', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '16rpx' }}>
          <Text style={{ fontSize: '30rpx', color: 'var(--ink)' }}>还没有项目</Text>
          <Text style={{ fontSize: '24rpx', color: 'var(--ink-3)' }}>创建一个项目，开始组织你的任务与笔记。</Text>
          <View className="btn-gold" style={{ padding: '16rpx 48rpx', fontSize: '26rpx' }} onClick={() => setShowNew(true)}>
            新建项目
          </View>
        </View>
      ) : (
        <ScrollView scrollY style={{ display: 'flex', flexDirection: 'column', gap: '20rpx' }}>
          {projects.map((p) => (
            <ProjectCard
              key={p.id}
              project={p}
              taskCount={tasks.filter((t) => t.project_id === p.id).length}
              noteCount={notes.filter((n) => n.project_id === p.id).length}
              onOpen={() => openProject(p.id)}
            />
          ))}
        </ScrollView>
      )}

      {/* AI 助手悬浮按钮 */}
      <View
        onClick={() => setAiOpen(true)}
        style={{
          position: 'fixed',
          right: '32rpx',
          bottom: '48rpx',
          width: '100rpx',
          height: '100rpx',
          borderRadius: '50%',
          background: 'linear-gradient(135deg,#E8C078,#A9762B)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          boxShadow: '0 0 20rpx rgba(217,164,65,0.45)',
          zIndex: 100,
        }}
      >
        <Text style={{ color: '#1A1406', fontSize: '40rpx', fontWeight: 700 }}>AI</Text>
      </View>

      <AiSheet open={aiOpen} onClose={() => setAiOpen(false)} />

      {/* 新建项目弹层 */}
      {showNew && (
        <View style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, zIndex: 999, background: 'rgba(0,0,0,0.62)' }} onClick={() => setShowNew(false)}>
          <View
            style={{ position: 'absolute', bottom: 0, left: 0, right: 0, background: 'var(--bg-elev-2)', borderTopLeftRadius: '32rpx', borderTopRightRadius: '32rpx', padding: '32rpx' }}
            onClick={(e) => e.stopPropagation()}
          >
            <Text style={{ fontSize: '32rpx', fontWeight: 600, color: 'var(--ink)', display: 'block', marginBottom: '24rpx' }}>新建项目</Text>
            <Input
              value={newName}
              onInput={(e) => setNewName(e.detail.value)}
              placeholder="项目名称"
              placeholderStyle="color:#6E6C64"
              style={{ height: '88rpx', background: 'var(--bg-elev-1)', border: '1rpx solid var(--border-soft)', borderRadius: '16rpx', padding: '0 24rpx', fontSize: '28rpx', color: 'var(--ink)', marginBottom: '20rpx' }}
            />
            <Input
              value={newDesc}
              onInput={(e) => setNewDesc(e.detail.value)}
              placeholder="一句话描述（可选）"
              placeholderStyle="color:#6E6C64"
              style={{ height: '88rpx', background: 'var(--bg-elev-1)', border: '1rpx solid var(--border-soft)', borderRadius: '16rpx', padding: '0 24rpx', fontSize: '28rpx', color: 'var(--ink)', marginBottom: '32rpx' }}
            />
            <View className="btn-gold" style={{ height: '84rpx', lineHeight: '84rpx', fontSize: '28rpx' }} onClick={() => createProject()}>
              创建
            </View>
          </View>
        </View>
      )}
    </View>
  )
}
