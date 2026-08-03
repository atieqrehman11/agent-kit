import { Link, useLocation } from 'react-router-dom'

import { defaultPath } from './registry'

/** Where every unknown path lands — including a roadmap feature's path, which
 * is registered in the nav but deliberately has no route. */
export function NotFound() {
  const { pathname } = useLocation()

  return (
    <div className="mx-auto max-w-lg p-8 text-center">
      <h2 className="text-lg font-semibold">Nothing here</h2>
      <p className="text-muted-foreground mt-2 text-sm">
        <span className="font-mono">{pathname}</span> is not a page in this app. It may be
        something on the roadmap that has not been built yet.
      </p>
      {defaultPath ? (
        <Link
          to={defaultPath}
          className="bg-primary text-primary-foreground mt-6 inline-block rounded-md px-4 py-2 text-sm font-medium"
        >
          Go to the start
        </Link>
      ) : null}
    </div>
  )
}
