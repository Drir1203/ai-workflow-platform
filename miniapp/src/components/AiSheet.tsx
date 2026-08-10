import { useState } from 'react'
import { Input, ScrollView, Text, View } from '@tarojs/components'
import { api } from '../api/client'

interface Msg {
  role: 'user' | 'assistant'
  text: string
}

const WELCOME: Msg = {
  role: 'assistant',
  text: '我是工作区 AI 助手。可以问我项目进度、任务待办或部署状态。',
}

export default function AiSheet({ open, onClose }: { open: boolean; onClose: () => void }) {
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
      const { answer } = await api.chat(q)
      setMsgs((m) => [...m, { role: 'assistant', text: answer }])
    } catch {
      setMsgs((m) => [...m, { role: 'assistant', text: '请求失败，请确认后端已配置 AI 引擎。' }])
    } finally {
      setBusy(false)
    }
  }

  if (!open) return null
  return (
    <View
      style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, zIndex: 1000, background: 'rgba(0,0,0,0.62)' }}
      onClick={onClose}
    >
      <View
        style={{
          position: 'absolute',
          bottom: 0,
          left: 0,
          right: 0,
          background: 'var(--bg-elev-2)',
          borderTopLeftRadius: '32rpx',
          borderTopRightRadius: '32rpx',
          padding: '28rpx',
          display: 'flex',
          flexDirection: 'column',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <View style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16rpx' }}>
          <View style={{ display: 'flex', alignItems: 'center', gap: '12rpx' }}>
            <View className="gold-dot" />
            <Text style={{ fontSize: '30rpx', fontWeight: 600, color: 'var(--ink)' }}>AI 助手</Text>
          </View>
          <Text onClick={onClose} style={{ fontSize: '30rpx', color: 'var(--ink-3)', padding: '8rpx' }}>✕</Text>
        </View>
        <ScrollView scrollY style={{ maxHeight: '46vh' }}>
          {msgs.map((m, i) => (
            <View key={i} style={{ display: 'flex', justifyContent: m.role === 'user' ? 'flex-end' : 'flex-start', marginBottom: '16rpx' }}>
              <Text
                style={{
                  maxWidth: '82%',
                  padding: '16rpx 20rpx',
                  borderRadius: '16rpx',
                  fontSize: '26rpx',
                  lineHeight: 1.6,
                  background: m.role === 'user' ? 'var(--gold-tint-bg)' : 'var(--bg-elev-1)',
                  color: m.role === 'user' ? 'var(--gold)' : 'var(--ink-2)',
                  border: m.role === 'user' ? '1rpx solid rgba(217,164,65,0.2)' : '1rpx solid var(--border-strong)',
                }}
              >
                {m.text}
              </Text>
            </View>
          ))}
          {busy && <Text style={{ color: 'var(--gold)', fontSize: '26rpx' }}>…</Text>}
        </ScrollView>
        <View style={{ display: 'flex', gap: '16rpx', marginTop: '20rpx' }}>
          <Input
            value={input}
            onInput={(e) => setInput(e.detail.value)}
            placeholder="问点什么…"
            placeholderStyle="color:#6E6C64"
            confirmType="send"
            onConfirm={() => send()}
            style={{
              flex: 1,
              height: '76rpx',
              background: 'var(--bg-elev-1)',
              border: '1rpx solid var(--border-soft)',
              borderRadius: '16rpx',
              padding: '0 22rpx',
              fontSize: '28rpx',
              color: 'var(--ink)',
            }}
          />
          <View className="btn-gold" style={{ width: '150rpx', height: '76rpx', lineHeight: '76rpx', fontSize: '26rpx' }} onClick={() => send()}>
            发送
          </View>
        </View>
      </View>
    </View>
  )
}
