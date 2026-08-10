import { View, Text } from '@tarojs/components'
import type { Task } from '../types'

const PRIORITY_COLOR: Record<string, string> = {
  high: '#E57373',
  medium: '#E5B567',
  low: '#8FA8C0',
}

export default function TaskItem({
  task,
  onToggle,
  onDelete,
}: {
  task: Task
  onToggle: () => void
  onDelete: () => void
}) {
  const done = task.status === 'done'
  const dot = PRIORITY_COLOR[task.priority] || '#8FA8C0'
  return (
    <View style={{ display: 'flex', alignItems: 'center', gap: '18rpx', padding: '22rpx 28rpx', borderBottom: '1rpx solid var(--border)' }}>
      <View
        onClick={onToggle}
        style={{
          width: '38rpx',
          height: '38rpx',
          borderRadius: '10rpx',
          border: done ? 'none' : '2rpx solid var(--border-strong)',
          background: done ? 'linear-gradient(135deg,#E8C078,#A9762B)' : 'transparent',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          flexShrink: 0,
        }}
      >
        {done && <Text style={{ color: '#1A1406', fontSize: '24rpx' }}>✓</Text>}
      </View>
      <Text
        style={{
          flex: 1,
          fontSize: '28rpx',
          color: done ? 'var(--ink-4)' : 'var(--ink)',
          textDecoration: done ? 'line-through' : 'none',
        }}
      >
        {task.title}
      </Text>
      {task.due_date && (
        <Text style={{ fontSize: '22rpx', color: done ? 'var(--ink-5)' : 'var(--ink-3)' }}>{task.due_date}</Text>
      )}
      <View style={{ width: '12rpx', height: '12rpx', borderRadius: '50%', background: dot, boxShadow: `0 0 8rpx ${dot}55` }} />
      <Text onClick={onDelete} style={{ fontSize: '24rpx', color: 'var(--ink-4)', padding: '8rpx 4rpx' }}>✕</Text>
    </View>
  )
}
