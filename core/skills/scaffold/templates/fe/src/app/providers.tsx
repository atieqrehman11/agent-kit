import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ThemeProvider } from 'next-themes'
import { useState, type ReactNode } from 'react'

/** Everything the app needs above the router. Split out from app.tsx so tests
 * can mount the same providers around a `MemoryRouter`. */
export function Providers({ children }: { children: ReactNode }) {
  // Created in state, not at module scope: a module-level client is shared
  // between tests and leaks one test's cache into the next.
  const [client] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            // No global staleTime. Each query sets its own, deliberately —
            // "how long is this data good for" is a question about the data,
            // and one answer for the whole app is an answer nobody gave.
            retry: 1,
            refetchOnWindowFocus: false,
          },
        },
      }),
  )

  return (
    <QueryClientProvider client={client}>
      {/* `class` because Tailwind's dark variant and globals.css both key off
          `.dark` on <html>. index.html ships with it already applied, so the
          first paint is not a flash of the wrong theme. */}
      <ThemeProvider attribute="class" defaultTheme="dark" enableSystem>
        {children}
      </ThemeProvider>
    </QueryClientProvider>
  )
}
