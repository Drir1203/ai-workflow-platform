// 相对时间格式化：通知列表用，避免引入 moment/dayjs 依赖

/** ISO 时间串 → 「刚刚 / N 分钟前 / N 小时前 / M月D日」。跨年显示完整日期。 */
export function formatRelativeTime(iso: string): string {
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return ''

  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const min = Math.floor(diffMs / 60_000)

  if (diffMs < 0 || min < 1) return '刚刚'
  if (min < 60) return `${min} 分钟前`
  const hours = Math.floor(min / 60)
  if (hours < 24) return `${hours} 小时前`

  const sameYear = date.getFullYear() === now.getFullYear()
  const label = `${date.getMonth() + 1}月${date.getDate()}日`
  return sameYear ? label : `${date.getFullYear()}年${label}`
}
