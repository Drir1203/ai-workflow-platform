import { View, Text } from '@tarojs/components'

const STATUS_MAP: Record<string, { color: string; label: string }> = {
  active: { color: '#7FD1A0', label: '进行中' },
  paused: { color: '#E5B567', label: '暂停' },
  archived: { color: '#8B877E', label: '已归档' },
}

export default function StatusBadge({ status }: { status: string }) {
  const s = STATUS_MAP[status] || { color: '#8FA8C0', label: status }
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
      <View style={{ width: '10rpx', height: '10rpx', borderRadius: '50%', background: s.color, boxShadow: `0 0 8rpx ${s.color}66` }} />
      <Text style={{ fontSize: '22rpx', color: s.color }}>{s.label}</Text>
    </View>
  )
}
