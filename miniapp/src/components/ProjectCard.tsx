import { View, Text } from '@tarojs/components'
import type { Project } from '../types'
import StatusBadge from './StatusBadge'

export default function ProjectCard({
  project,
  taskCount,
  noteCount,
  onOpen,
}: {
  project: Project
  taskCount: number
  noteCount: number
  onOpen: () => void
}) {
  return (
    <View
      className="card"
      onClick={onOpen}
      style={{ padding: '28rpx', display: 'flex', flexDirection: 'column', gap: '14rpx' }}
    >
      <View style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '16rpx' }}>
        <Text style={{ fontSize: '30rpx', fontWeight: 600, color: 'var(--ink)', flex: 1 }}>{project.name}</Text>
        <StatusBadge status={project.status} />
      </View>
      {project.description && (
        <Text style={{ fontSize: '24rpx', color: 'var(--ink-3)' }} numberOfLines={2}>{project.description}</Text>
      )}
      <View style={{ display: 'flex', gap: '28rpx', fontSize: '22rpx', color: 'var(--ink-5)' }}>
        <Text><Text className="num">{taskCount}</Text> 任务</Text>
        <Text><Text className="num">{noteCount}</Text> 笔记</Text>
      </View>
    </View>
  )
}
