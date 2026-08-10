import { View, Text } from '@tarojs/components'

export default function StatCard({ label, value, sub }: { label: string; value: string | number; sub?: string }) {
  return (
    <View className="card" style={{ padding: '24rpx' }}>
      <Text style={{ fontSize: '22rpx', color: 'var(--ink-4)' }}>{label}</Text>
      <View className="num" style={{ fontSize: '44rpx', fontWeight: 600, marginTop: '6rpx' }}>{value}</View>
      {sub && <Text style={{ fontSize: '22rpx', color: 'var(--ink-5)' }}>{sub}</Text>}
    </View>
  )
}
