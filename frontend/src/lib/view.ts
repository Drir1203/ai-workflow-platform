export type View =
  | { name: 'dashboard' }
  | { name: 'project'; id: string }
  | { name: 'agents' }
  | { name: 'workflows' }
  | { name: 'team' }

import type { demoApi } from './demo'

export type DataLayer = typeof demoApi
