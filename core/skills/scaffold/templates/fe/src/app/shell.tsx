import { Moon, Sun } from 'lucide-react'
import { useTheme } from 'next-themes'
import { NavLink, Outlet } from 'react-router-dom'

import { cn } from '@/shared/lib/cn'

import { APP_NAME } from './app-info'
import { FEATURES } from './registry'

/** The application shell: title, navigation, theme toggle, feature slot.
 *
 * Nothing here knows any feature by name — the nav is built from the registry,
 * so adding a feature never edits this file. */

function ThemeToggle() {
  const { resolvedTheme, setTheme } = useTheme()
  const next = resolvedTheme === 'dark' ? 'light' : 'dark'

  return (
    <button
      type="button"
      onClick={() => setTheme(next)}
      // The label says what will happen, not what is currently true — that is
      // what a screen reader user needs before activating it.
      aria-label={`Switch to ${next} theme`}
      className="hover:bg-accent rounded-md p-2"
    >
      {resolvedTheme === 'dark' ? (
        <Sun className="size-4" aria-hidden />
      ) : (
        <Moon className="size-4" aria-hidden />
      )}
    </button>
  )
}

export function Shell() {
  return (
    <div className="flex min-h-full flex-col">
      {/* Keyboard users reach the content without tabbing the whole nav. It is
          visually hidden until focused, which is the only correct way to do it —
          `display: none` would take it out of the tab order entirely. */}
      <a
        href="#main"
        className="bg-primary text-primary-foreground sr-only focus:not-sr-only focus:absolute focus:top-2 focus:left-2 focus:z-50 focus:rounded-md focus:px-3 focus:py-2"
      >
        Skip to content
      </a>

      <header className="border-border flex items-center gap-6 border-b px-6 py-3">
        <span className="font-semibold">{APP_NAME}</span>

        <nav aria-label="Sections" className="flex flex-1 items-center gap-1">
          {FEATURES.map((feature) =>
            feature.status === 'live' ? (
              <NavLink
                key={feature.id}
                to={feature.path}
                title={feature.description}
                className={({ isActive }) =>
                  cn(
                    'flex items-center gap-2 rounded-md px-3 py-1.5 text-sm',
                    isActive
                      ? 'bg-accent text-accent-foreground font-medium'
                      : 'text-muted-foreground hover:text-foreground',
                  )
                }
              >
                <feature.icon className="size-4" aria-hidden />
                {feature.title}
              </NavLink>
            ) : (
              <span
                key={feature.id}
                // Not a link and not a disabled button: there is nothing to
                // activate, so it must not be focusable or announced as a
                // control. The suffix carries the meaning without relying on
                // colour alone.
                className="text-muted-foreground/60 flex items-center gap-2 px-3 py-1.5 text-sm"
                title={feature.description}
              >
                <feature.icon className="size-4" aria-hidden />
                {feature.title}
                <span className="text-xs">(soon)</span>
              </span>
            ),
          )}
        </nav>

        <ThemeToggle />
      </header>

      <main id="main" className="flex-1">
        <Outlet />
      </main>
    </div>
  )
}
