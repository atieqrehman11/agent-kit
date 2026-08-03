import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'

import { Providers } from './providers'
import { FEATURES, isLive } from './registry'
import { AppRoutes } from './routes'

/** The registry contract.
 *
 * These tests are the reason "add a feature = one registry entry" stays true:
 * they assert the derivation itself, so a shell that quietly stops reading the
 * registry fails here rather than in review. */

function renderAt(path: string) {
  return render(
    <Providers>
      <MemoryRouter initialEntries={[path]}>
        <AppRoutes />
      </MemoryRouter>
    </Providers>,
  )
}

describe('feature registry', () => {
  it('has unique ids and paths', () => {
    const ids = FEATURES.map((f) => f.id)
    const paths = FEATURES.map((f) => f.path)
    expect(new Set(ids).size).toBe(ids.length)
    expect(new Set(paths).size).toBe(paths.length)
  })

  it('uses leading-slash paths', () => {
    for (const feature of FEATURES) {
      expect(feature.path.startsWith('/')).toBe(true)
    }
  })

  it('lists every feature in the navigation, live or not', () => {
    renderAt('/')
    const nav = screen.getByRole('navigation', { name: /sections/i })
    for (const feature of FEATURES) {
      expect(nav).toHaveTextContent(feature.title)
    }
  })

  it('links only to live features', () => {
    renderAt('/')
    const nav = screen.getByRole('navigation', { name: /sections/i })
    const links = screen.getAllByRole('link').filter((link) => nav.contains(link))
    expect(links).toHaveLength(FEATURES.filter(isLive).length)
  })

  it('routes every live feature', async () => {
    for (const feature of FEATURES.filter(isLive)) {
      const { unmount } = renderAt(feature.path)
      // Lazy chunk — the assertion has to wait for the import to resolve.
      expect(await screen.findByRole('main')).not.toBeEmptyDOMElement()
      expect(screen.queryByText(/not a page in this app/i)).not.toBeInTheDocument()
      unmount()
    }
  })

  it('routes no roadmap feature', async () => {
    for (const feature of FEATURES.filter((f) => !isLive(f))) {
      const { unmount } = renderAt(feature.path)
      expect(await screen.findByText(/not a page in this app/i)).toBeInTheDocument()
      unmount()
    }
  })

  it('sends an unknown path to the 404 surface', async () => {
    renderAt('/definitely-not-a-feature')
    expect(await screen.findByText(/not a page in this app/i)).toBeInTheDocument()
  })
})
