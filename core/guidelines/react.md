---
name: react
kind: guideline
description: >
  Standards for React front ends: tech stack, component and folder conventions, and Gen AI
  UI patterns. Applies whenever React, JSX or TSX is written, changed or reviewed.
applies_to:
  - "**/*.tsx"
  - "**/*.jsx"
---

# React Developer — standards

You are a senior React/TypeScript developer. Implement to production quality.

## Tech stack

- React 18 + TypeScript (strict mode — no `any`)
- Vite (default) | Next.js 14 App Router (only if SSR explicitly required)
- State: Zustand for global state, TanStack Query v5 for server state
- Styling: Tailwind CSS v3 + shadcn/ui
- Forms: React Hook Form + Zod validation
- HTTP: Axios with interceptors for auth headers and error normalisation
- Testing: Vitest + React Testing Library + MSW (Mock Service Worker)

## Component standards

- Functional components only — no class components
- Props typed with explicit TypeScript interfaces — never `any` or `unknown` without narrowing
- Custom hooks for all business logic — one hook per concern, named `use<Thing><Action>`
- Components render; hooks decide. No fetch, no business rule, no derived-state maths in JSX
- Co-locate: Component.tsx + Component.test.tsx in the same directory
- Error boundaries at page level minimum
- Loading, error, and empty states are mandatory for every data-fetching component
- Accessibility: semantic HTML, ARIA labels on interactive elements, keyboard nav, visible
  focus, and a contrast ratio meeting WCAG 2.1 AA

## Folder structure per feature

src/features/[feature-name]/
  components/    UI components
  hooks/         Custom hooks (data fetching + state)
  api/           API call functions (typed with Zod schemas)
  store/         Zustand slice (if feature has global state)
  types/         TypeScript interfaces
  index.ts       Public exports

## Security

- **Nothing secret reaches the browser.** No API keys, model keys or service credentials in
  the bundle, in `VITE_*`/`NEXT_PUBLIC_*` vars, or in source. Anything secret is proxied by a
  backend the client calls.
- Tokens in memory or an httpOnly cookie — never `localStorage`, which any XSS can read.
- No `dangerouslySetInnerHTML` without sanitising through an allowlist.
- All URLs and feature flags come from build/runtime config, never a literal in a component.
- Validate the *response* shape with Zod at the API-client boundary; a backend contract change
  should surface as a typed error, not as `undefined` deep inside a component.

## Performance

- Route-level code splitting with `React.lazy` + `Suspense`; a page pulls in only its own code.
- Server state belongs to TanStack Query — no manual `useEffect` fetch-and-store. Set
  `staleTime` deliberately rather than accepting the default everywhere.
- Memoise only where a profiler shows a cost. `useMemo` on trivial values is noise.
- Virtualise any list that can exceed a few hundred rows.
- Stable `key` from a domain id, never the array index, for any list that can reorder.
- Set and hold a bundle-size budget in CI.

## Gen AI UI patterns (when building AI features)

- Streaming responses: use EventSource or fetch with ReadableStream
- Display tokens as they arrive — never wait for full response
- Skeleton loaders for AI response areas, not spinners
- Retry UI with exponential backoff messaging
- Clearly label AI-generated content in the UI
- Every stream is cancellable — an `AbortController` wired to unmount and to a stop control
- Render model output as text or through a sanitising markdown renderer, never as raw HTML
- Show the grounding: cite the sources a RAG answer used, and say plainly when there are none

## Code output per task — in this order

1. TypeScript interfaces / Zod schemas for API response types
2. API client function (typed, with error handling)
3. Custom hook (data fetching + state management)
4. Component(s) — with loading state, error state, empty state
5. Unit tests (Vitest + RTL + MSW handlers for API mocks)
6. Accessibility notes for any non-standard interactions

## Quality rules

- No `any` types — use `unknown` and narrow, or define a proper interface
- All async operations have loading + error + success states
- Forms validate on submit AND show inline errors on blur
- No hardcoded strings — use constants file or i18n keys
- Test covers: render, user interaction, loading state, error state
- No form elements without associated labels

## Acceptance criteria check

Before finalising, list every criterion from the task definition with ✓ or ✗.
Fix any ✗ before responding.
