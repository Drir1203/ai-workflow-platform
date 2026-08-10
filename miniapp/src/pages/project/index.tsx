import { useCallback, useMemo, useState } from 'react'
import { Button, Input, Picker, ScrollView, Text, View } from '@tarojs/components'
import Taro, { useRouter, useDidShow } from '@tarojs/taro'
import { api } from '../../api/client'
import { TEMPLATE_DUE } from '../../api/config'
import AiSheet from '../../components/AiSheet'
import NoteItem from '../../components/NoteItem'
import StatusBadge from '../../components/StatusBadge'
import TaskItem from '../../components/TaskItem'
import type { Note, Project, Task } from '../../types'

export default function Project() {
  const { id } = useRouter().params
  const [project, setProject] = useState<Project | null>(null)
  const [tasks, setTasks] = useState<Task[]>([])
  const [notes, setNotes] = useState<Note[]>([])
  const [taskTitle, setTaskTitle] = useState('')
  const [priority, setPriority] = useState('medium')
  const [dueDate, setDueDate] = useState('')
  const [noteTitle, setNoteTitle] = useState('')
  const [noteContent, setNoteContent] = useState('')
  const [aiOpen, setAiOpen] = useState(false)
  const [showTaskForm, setShowTaskForm] = useState(false)

  const load = useCallback(async () => {
    if (!id) return
    try {
      const [ps, ts, ns] = await Promise.all([api.listProjects(), api.listTasks(id), api.listNotes(id)])
      setProject(ps.find((p) => p.id === id) || null)
      setTasks(ts)
      setNotes(ns)
    } catch (e: any) {
      Taro.showToast({ title: e.message || '加载失败', icon: 'none' })
    }
  }, [id])

  useDidShow(load)

  const stats = useMemo(
    () => ({ total: tasks.length, done: tasks.filter((t) => t.status === 'done').length }),
    [tasks],
  )

  async function createTask() {
    if (!taskTitle.trim()) return
    try {
      const task = await api.createTask({
        project_id: id!,
        title: taskTitle.trim(),
        priority,
        due_date: dueDate || null,
      })
      setTaskTitle('')
      setDueDate('')
      setShowTaskForm(false)
      load()
      if (task.due_date) bindSubscription(task.id)
    } catch (e: any) {
      Taro.showToast({ title: e.message || '创建失败', icon: 'none' })
    }
  }

  async function toggleTask(task: Task) {
    await api.updateTask(task.id, { status: task.status === 'done' ? 'todo' : 'done' })
    load()
  }

  async function deleteTask(taskId: string) {
    const res = await Taro.showModal({ title: '删除任务', content: '确定删除该任务？' })
    if (res.confirm) {
      await api.deleteTask(taskId)
      load()
    }
  }

  async function bindSubscription(taskId: string) {
    if (!TEMPLATE_DUE) return
    try {
      const subRes = await Taro.requestSubscribeMessage({ tmplIds: [TEMPLATE_DUE] })
      const accepted = subRes[TEMPLATE_DUE] === 'accept'
      if (!accepted) return
      const loginRes = await Taro.login()
      if (loginRes.code) {
        await api.wechatSubscribe(loginRes.code, taskId, TEMPLATE_DUE)
        Taro.showToast({ title: '已订阅到期提醒', icon: 'success' })
      }
    } catch {
      // 用户取消或环境不支持，静默
    }
  }

  async function createNote() {
    if (!noteTitle.trim()) return
    try {
      await api.createNote({ project_id: id!, title: noteTitle.trim(), content: noteContent.trim() || undefined })
      setNoteTitle('')
      setNoteContent('')
      load()
    } catch (e: any) {
      Taro.showToast({ title: e.message || '保存失败', icon: 'none' })
    }
  }

  async function deleteNote(noteId: string) {
    const res = await Taro.showModal({ title: '删除笔记', content: '确定删除该笔记？' })
    if (res.confirm) {
      await api.deleteNote(noteId)
      load()
    }
  }

  if (!project) {
    return (
      <View style={{ padding: '60rpx', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '20rpx' }}>
        <Text style={{ fontSize: '30rpx', color: 'var(--ink)' }}>项目不存在或已被删除</Text>
        <View className="btn-ghost" style={{ padding: '16rpx 40rpx', fontSize: '26rpx' }} onClick={() => Taro.navigateBack()}>
          返回工作台
        </View>
      </View>
    )
  }

  return (
    <View style={{ padding: '28rpx', paddingBottom: '160rpx' }}>
      <View style={{ display: 'flex', alignItems: 'center', gap: '12rpx', marginBottom: '24rpx' }}>
        <Text onClick={() => Taro.navigateBack()} style={{ fontSize: '28rpx', color: 'var(--ink-3)' }}>‹ 返回</Text>
      </View>

      <View style={{ marginBottom: '32rpx' }}>
        <View style={{ display: 'flex', alignItems: 'center', gap: '20rpx', flexWrap: 'wrap' }}>
          <Text style={{ fontSize: '40rpx', fontWeight: 650, color: 'var(--ink)', flex: 1 }}>{project.name}</Text>
          <StatusBadge status={project.status} />
        </View>
        {project.description && (
          <Text style={{ fontSize: '26rpx', color: 'var(--ink-3)', marginTop: '10rpx', display: 'block' }}>{project.description}</Text>
        )}
        <View style={{ display: 'flex', gap: '28rpx', marginTop: '16rpx', fontSize: '24rpx', color: 'var(--ink-4)' }}>
          <Text><Text className="num">{stats.total}</Text> 任务</Text>
          <Text><Text className="num">{stats.done}</Text> 完成</Text>
          <Text><Text className="num">{notes.length}</Text> 笔记</Text>
        </View>
      </View>

      {/* 任务区 */}
      <View className="card" style={{ overflow: 'hidden', marginBottom: '32rpx' }}>
        <View style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '24rpx 28rpx', borderBottom: '1rpx solid var(--border)' }}>
          <Text style={{ fontSize: '30rpx', fontWeight: 600, color: 'var(--ink-2)' }}>任务</Text>
          <Text onClick={() => setShowTaskForm((s) => !s)} style={{ fontSize: '26rpx', color: 'var(--gold)' }}>
            {showTaskForm ? '收起' : '+ 添加任务'}
          </Text>
        </View>

        {showTaskForm && (
          <View style={{ padding: '24rpx 28rpx', borderBottom: '1rpx solid var(--border)', background: 'var(--bg-elev-1)' }}>
            <Input
              value={taskTitle}
              onInput={(e) => setTaskTitle(e.detail.value)}
              placeholder="任务标题"
              placeholderStyle="color:#6E6C64"
              style={{ height: '80rpx', background: 'var(--bg-elev-2)', border: '1rpx solid var(--border-soft)', borderRadius: '14rpx', padding: '0 20rpx', fontSize: '28rpx', color: 'var(--ink)', marginBottom: '16rpx' }}
            />
            <View style={{ display: 'flex', gap: '16rpx', alignItems: 'center', marginBottom: '16rpx' }}>
              <Picker mode="selector" range={['high', 'medium', 'low']} onChange={(e) => setPriority(['high', 'medium', 'low'][Number(e.detail.value)])}>
                <View style={{ padding: '14rpx 24rpx', borderRadius: '12rpx', border: '1rpx solid var(--border-strong)', fontSize: '24rpx', color: 'var(--ink-2)' }}>
                  优先级 · {priority}
                </View>
              </Picker>
              <Picker mode="date" onChange={(e) => setDueDate(e.detail.value)}>
                <View style={{ padding: '14rpx 24rpx', borderRadius: '12rpx', border: '1rpx solid var(--border-strong)', fontSize: '24rpx', color: dueDate ? 'var(--gold)' : 'var(--ink-2)' }}>
                  {dueDate || '截止日期'}
                </View>
              </Picker>
            </View>
            <View className="btn-gold" style={{ height: '76rpx', lineHeight: '76rpx', fontSize: '28rpx' }} onClick={() => createTask()}>
              创建任务
            </View>
          </View>
        )}

        {tasks.length === 0 ? (
          <View style={{ padding: '60rpx 28rpx', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '12rpx' }}>
            <Text style={{ fontSize: '28rpx', color: 'var(--ink)' }}>还没有任务</Text>
            <Text style={{ fontSize: '24rpx', color: 'var(--ink-4)' }}>添加第一个任务，开始推进这个项目。</Text>
          </View>
        ) : (
          tasks.map((t) => (
            <TaskItem key={t.id} task={t} onToggle={() => toggleTask(t)} onDelete={() => deleteTask(t.id)} />
          ))
        )}
      </View>

      {/* 笔记区 */}
      <View style={{ marginBottom: '32rpx' }}>
        <Text style={{ fontSize: '30rpx', fontWeight: 600, color: 'var(--ink-2)', marginBottom: '20rpx', display: 'block' }}>笔记</Text>
        <View className="card" style={{ padding: '24rpx', marginBottom: '20rpx' }}>
          <Input
            value={noteTitle}
            onInput={(e) => setNoteTitle(e.detail.value)}
            placeholder="笔记标题"
            placeholderStyle="color:#6E6C64"
            style={{ height: '80rpx', background: 'var(--bg-elev-1)', border: '1rpx solid var(--border-soft)', borderRadius: '14rpx', padding: '0 20rpx', fontSize: '28rpx', color: 'var(--ink)', marginBottom: '16rpx' }}
          />
          <Input
            value={noteContent}
            onInput={(e) => setNoteContent(e.detail.value)}
            placeholder="随手记…"
            placeholderStyle="color:#6E6C64"
            style={{ height: '80rpx', background: 'var(--bg-elev-1)', border: '1rpx solid var(--border-soft)', borderRadius: '14rpx', padding: '0 20rpx', fontSize: '28rpx', color: 'var(--ink)', marginBottom: '16rpx' }}
          />
          <Button className="btn-ghost" style={{ height: '72rpx', lineHeight: '72rpx', fontSize: '26rpx' }} onClick={() => createNote()}>
            保存笔记
          </Button>
        </View>
        <View style={{ display: 'flex', flexDirection: 'column', gap: '20rpx' }}>
          {notes.length === 0 ? (
            <Text style={{ fontSize: '24rpx', color: 'var(--ink-5)', textAlign: 'center', padding: '24rpx' }}>还没有笔记</Text>
          ) : (
            notes.map((n) => <NoteItem key={n.id} note={n} onDelete={() => deleteNote(n.id)} />)
          )}
        </View>
      </View>

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
    </View>
  )
}
