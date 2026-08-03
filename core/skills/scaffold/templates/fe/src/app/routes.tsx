import { Suspense } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'

import { ErrorBoundary } from './error-boundary'
import { NotFound } from './not-found'
import { Shell } from './shell'
import { defaultPath, FEATURES, isLive, type LiveFeature } from './registry'

/** Routes, derived from the registry. Exported without a Router around it so a
 * test can mount it inside a `MemoryRouter` — see registry.test.tsx. */

function FeatureSlot({ feature }: { feature: LiveFeature }) {
  const { Component } = feature
  return (
    <ErrorBoundary resetKey={feature.id}>
      {/* A skeleton, not a spinner: the chunk is already downloading, and a
          shape that matches what is coming reads as fast rather than as stuck. */}
      <Suspense fallback={<div className="bg-muted/40 m-6 h-64 animate-pulse rounded-lg" />}>
        <Component />
      </Suspense>
    </ErrorBoundary>
  )
}

export function AppRoutes() {
  return (
    <Routes>
      <Route element={<Shell />}>
        {defaultPath ? <Route index element={<Navigate to={defaultPath} replace />} /> : null}
        {FEATURES.filter(isLive).map((feature) => (
          <Route
            key={feature.id}
            path={feature.path}
            element={<FeatureSlot feature={feature} />}
          />
        ))}
        {/* Everything else, including a roadmap feature's path. */}
        <Route path="*" element={<NotFound />} />
      </Route>
    </Routes>
  )
}
