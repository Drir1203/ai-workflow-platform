export type View = { name: 'dashboard' } | { name: 'project'; id: string }

import type { demoApi } from './demo'

export type DataLayer = typeof demoApi
