export type ThemeId = 'obsidian' | 'aurora' | 'deepspace' | 'crystal'

export interface ThemeDef {
  id: ThemeId
  label: string
  hint: string
  swatch: { bg: string; gold: string }
}

export const THEMES: ThemeDef[] = [
  { id: 'obsidian', label: '黑金旗舰', hint: '暖炭黑 · 香槟金', swatch: { bg: '#0C0C0B', gold: '#D9A441' } },
  { id: 'aurora', label: '通透光感', hint: '象牙白 · 浅金', swatch: { bg: '#F7F3EA', gold: '#A07A1B' } },
  { id: 'deepspace', label: '深空蓝金', hint: '冷深空 · 金', swatch: { bg: '#080B10', gold: '#D9A441' } },
  { id: 'crystal', label: '晶界金', hint: '石墨灰 · 亮金', swatch: { bg: '#0E0E10', gold: '#DFAF4F' } },
]

const KEY = 'ph_theme'

export function isThemeId(v: unknown): v is ThemeId {
  return typeof v === 'string' && THEMES.some((t) => t.id === v)
}

export function getTheme(): ThemeId {
  const raw = localStorage.getItem(KEY)
  return isThemeId(raw) ? raw : 'obsidian'
}

export function applyTheme(id: ThemeId) {
  localStorage.setItem(KEY, id)
  document.documentElement.dataset.theme = id
}

export function initTheme(): ThemeId {
  const id = getTheme()
  document.documentElement.dataset.theme = id
  return id
}
