import { useState } from 'react'
import { Button, Input, Text, View } from '@tarojs/components'
import Taro from '@tarojs/taro'
import { api, setSession } from '../../api/client'

export default function Login() {
  const [tab, setTab] = useState<'login' | 'register'>('login')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [name, setName] = useState('')
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState('')

  async function submit() {
    if (busy) return
    setErr('')
    setBusy(true)
    try {
      const r =
        tab === 'login'
          ? await api.login(email.trim(), password)
          : await api.register(email.trim(), password, name.trim())
      setSession(r)
      Taro.reLaunch({ url: '/pages/dashboard/index' })
    } catch (e: any) {
      setErr(e.message || '操作失败')
    } finally {
      setBusy(false)
    }
  }

  return (
    <View style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column', padding: '60rpx', background: 'var(--bg)' }}>
      <View style={{ marginTop: '20vh', marginBottom: '80rpx' }}>
        <View style={{ width: '96rpx', height: '96rpx', borderRadius: '24rpx', background: 'linear-gradient(135deg,#E8C078,#A9762B)', display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: '28rpx' }}>
          <Text style={{ color: '#1A1406', fontSize: '44rpx', fontWeight: 700 }}>P</Text>
        </View>
        <Text style={{ fontSize: '48rpx', fontWeight: 650, color: 'var(--ink)', letterSpacing: '-1rpx' }}>AI智序</Text>
        <Text style={{ fontSize: '26rpx', color: 'var(--ink-3)', marginTop: '12rpx' }}>管理你的项目、任务与 AI 工作流</Text>
      </View>

      <View style={{ display: 'flex', gap: '24rpx', marginBottom: '40rpx' }}>
        {(['login', 'register'] as const).map((t) => (
          <Text
            key={t}
            onClick={() => { setTab(t); setErr('') }}
            style={{
              fontSize: '30rpx',
              paddingBottom: '12rpx',
              borderBottom: tab === t ? '4rpx solid var(--gold-primary)' : '4rpx solid transparent',
              color: tab === t ? 'var(--gold)' : 'var(--ink-3)',
              fontWeight: tab === t ? 600 : 400,
            }}
          >
            {t === 'login' ? '登录' : '注册'}
          </Text>
        ))}
      </View>

      {tab === 'register' && (
        <Input
          value={name}
          onInput={(e) => setName(e.detail.value)}
          placeholder="昵称"
          placeholderStyle="color:#6E6C64"
          style={inputStyle}
        />
      )}
      <Input
        value={email}
        onInput={(e) => setEmail(e.detail.value)}
        placeholder="邮箱"
        placeholderStyle="color:#6E6C64"
        type="text"
        style={inputStyle}
      />
      <Input
        value={password}
        onInput={(e) => setPassword(e.detail.value)}
        placeholder="密码（至少 8 位）"
        placeholderStyle="color:#6E6C64"
        password
        style={inputStyle}
      />

      {err && <Text style={{ fontSize: '24rpx', color: 'var(--error)', marginTop: '16rpx' }}>{err}</Text>}

      <Button
        className="btn-gold"
        loading={busy}
        onClick={() => submit()}
        style={{ marginTop: '40rpx', height: '88rpx', lineHeight: '88rpx', fontSize: '30rpx' }}
      >
        {tab === 'login' ? '登录' : '注册并登录'}
      </Button>
    </View>
  )
}

const inputStyle = {
  height: '88rpx',
  background: 'var(--bg-elev-1)',
  border: '1rpx solid var(--border-soft)',
  borderRadius: '16rpx',
  padding: '0 24rpx',
  fontSize: '28rpx',
  color: 'var(--ink)',
  marginBottom: '24rpx',
}
