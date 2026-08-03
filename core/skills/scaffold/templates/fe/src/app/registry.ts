import { lazy, type ComponentType, type LazyExoticComponent } from 'react'
import { LayoutDashboard, type LucideIcon } from 'lucide-react'

/** The feature registry — the one place that knows what this app contains.
 *
 * Navigation and routing are both DERIVED from this array, which is what makes
 * "add a feature" a one-entry change: no shell file is edited, so no shell file
 * can be forgotten. If you find yourself editing shell.tsx or routes.tsx to add
 * a feature, the registry has stopped being the source of truth and the next
 * feature will cost the same again.
 *
 * `status: 'soon'` is a roadmap entry: it shows in the nav as unavailable and
 * registers NO route, so its URL reaches the 404 surface like any other unknown
 * path. A disabled link that still routes to a half-built page is worse than no
 * link at all.
 *
 * Every live feature is `React.lazy`, so each one is its own chunk and the
 * initial load pays for the shell alone. */

interface FeatureBase {
  /** Stable id — used as a React key and in the registry test. Never rendered. */
  id: string
  title: string
  /** One line, shown in nav tooltips and on the overview. */
  description: string
  /** Route path, leading slash. */
  path: string
  icon: LucideIcon
}

export type Feature =
  | (FeatureBase & { status: 'live'; Component: LazyExoticComponent<ComponentType> })
  | (FeatureBase & { status: 'soon' })

export type LiveFeature = Extract<Feature, { status: 'live' }>

export const FEATURES: readonly Feature[] = [
  {
    id: 'overview',
    title: 'Overview',
    description: 'What this app does, and what to build next.',
    path: '/overview',
    icon: LayoutDashboard,
    status: 'live',
    Component: lazy(() => import('@/features/overview')),
  },
  // Add a feature by adding an entry here:
  //
  // {
  //   id: 'anomalies',
  //   title: 'Anomalies',
  //   description: 'Signals that fell outside their expected band.',
  //   path: '/anomalies',
  //   icon: TriangleAlert,
  //   status: 'live',
  //   Component: lazy(() => import('@/features/anomalies')),
  // },
]

export function isLive(feature: Feature): feature is LiveFeature {
  return feature.status === 'live'
}

/** Where `/` sends you — the first live feature, in registry order. */
export const defaultPath = FEATURES.find(isLive)?.path
