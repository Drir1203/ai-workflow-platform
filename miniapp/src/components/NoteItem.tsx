import { View, Text } from '@tarojs/components'
import type { Note } from '../types'

export default function NoteItem({ note, onDelete }: { note: Note; onDelete: () => void }) {
  return (
    <View className="card" style={{ padding: '24rpx' }}>
      <View style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <Text style={{ fontSize: '28rpx', fontWeight: 600, color: 'var(--ink)' }}>{note.title}</Text>
        <Text onClick={onDelete} style={{ fontSize: '24rpx', color: 'var(--ink-4)', padding: '8rpx 4rpx' }}>✕</Text>
      </View>
      {note.content && (
        <Text style={{ fontSize: '24rpx', color: 'var(--ink-3)', marginTop: '10rpx', display: 'block' }}>{note.content}</Text>
      )}
    </View>
  )
}
