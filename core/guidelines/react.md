---
name: react
kind: guideline
description: >
  Standards for React front ends: tech stack, the shell/feature split, theming, data access,
  and the rules a Databricks App front end must meet. Applies whenever React, JSX or TSX is
  written, changed or reviewed.
applies_to:
  - "**/*.tsx"
  - "**/*.jsx"
---

# React Developer — standards

You are a senior React/TypeScript developer. Implement to production quality.

The audit list for these rules is [`conformance/react.md`](conformance/react.md).

## Tech stack

- React 19 + TypeScript `strict` — no `any`, no `as T` on untrusted data
- Vite. Next.js only if server rendering is a stated requirement, which for an internal
  dashboard it usually is not
- Styling: Tailwind v4, configured CSS-first with `@theme` in one stylesheet. There is no
  `tailwind.config.js`
- Components: shadcn/ui for anything with behaviour — dialogs, dropdowns, comboboxes, tabs,
  tooltips, command palettes. Hand-rolling one of these means re-deriving its focus and
  keyboard semantics, and the second attempt is never as good as the vendored one
- Data grids: TanStack Table. No bespoke sort/filter/paginate logic
- Server state: TanStack Query v5. No `useEffect` fetch-and-store
- Global state: none by default. Add a store only when a feature demonstrably needs state that
  outlives its route, and then only for that feature
- HTTP: one typed `fetch` client. No Axios — the interceptor stack it exists for is a
  `fetch` wrapper of about forty lines here
- Validation: Zod at the API boundary, and for form schemas
- Testing: Vitest + React Testing Library + MSW

## Shell and features

The shell is generic; features are the only thing that grows.

- **One feature registry drives both navigation and routing.** A feature declares its id,
  title, path, status and lazy component in one place; nav and routes are derived from it
- Adding a feature must require **no edit to a shell file**. If it does, the registry is not
  actually the source of truth
- A roadmap feature (`status: 'soon'`) appears in nav as unavailable and registers **no
  route** — its URL reaches the 404 surface like any other unknown path
- Every feature component is `React.lazy`, so each feature is its own chunk
- **No feature imports another feature.** They talk through `@/shared` and `@/app`, and
  `no-restricted-imports` enforces it. Inside a feature, reach your own files by relative
  path — not through the feature's own alias, which is what keeps it movable
- An error boundary wraps the feature slot, so one feature's crash does not take the shell

### Folder structure per feature

```
src/features/<feature>/
  components/    UI components (thing-card.tsx + thing-card.test.tsx side by side)
  hooks/         custom hooks — data fetching + state
  api/           API call functions, Zod-typed
  types/         shared interfaces
  index.ts       the public entry the registry lazy-loads
```

### Naming

File names and export names are governed by different things — the filesystem and the
JavaScript grammar — so they are two rules, not one:

- **Files and folders are `kebab-case`**, always: `thing-card.tsx`, `use-thing-data.ts`,
  `error-boundary.tsx`, `globals.css`. No exceptions, including for a file that holds a
  single component.
- **Exports are cased for what they are.** `PascalCase` for components and types,
  `camelCase` for functions and hooks, `SCREAMING_SNAKE_CASE` for constants. So
  `thing-card.tsx` exports `ThingCard`.

Two reasons the file half is kebab rather than matching the component:

1. **shadcn/ui writes kebab and overwrites it.** `shadcn add` emits `dropdown-menu.tsx`,
   `alert-dialog.tsx` into `src/shared/ui/`, and re-running it replaces those files
   wholesale — they cannot be renamed and kept. PascalCase elsewhere buys a permanently
   mixed tree rather than a consistent one.
2. **macOS and Windows filesystems are case-insensitive.** A rename that only changes case
   needs two commits to land, and the import that resolved locally 404s on a
   case-sensitive CI runner.

PascalCase on the export is not a preference. JSX resolves `<Thing />` to a variable and
`<thing />` to the string `"thing"`, so a lowercase component silently renders an unknown
DOM element instead of erroring. `react/jsx-pascal-case` enforces it.

## Components

- Functional components only. Props typed with explicit interfaces
- Custom hooks for business logic — one hook per concern, named `use<Thing><Action>`
- **Components render; hooks decide.** No fetch, no business rule, no derived-state maths
  in JSX
- Co-locate `thing-card.tsx` with `thing-card.test.tsx`
- Loading, error **and** empty states are mandatory for every data-fetching component. An
  empty result renders as empty, not as an error

## Complexity limits

Same thresholds as [`python`](./python.md) and [`java`](./java.md), via ESLint. Set them as
`error` — a warning in a front-end build is invisible within a week.

```json
{
  "rules": {
    "complexity": ["error", 10],
    "max-depth": ["error", 4],
    "max-statements": ["error", 50],
    "max-params": ["error", 5],
    "react/jsx-max-depth": ["error", { "max": 4 }]
  }
}
```

**Depth shows up twice in this stack**, and both count. In **logic** — nested conditionals in a
hook or handler; fix with an early return, or move the decision into a hook where it can be
tested without rendering. In **JSX** — nested ternaries and deep conditional markup; extract a
component, or compute the branch above the `return` as a named variable
(`react/jsx-no-leaked-render` catches the related `&&` bug).

**A component past ~150 lines is doing more than one thing**, and the seam is almost always a
hook — *Components render; hooks decide* is single responsibility stated for this stack. Tells:
a component that both fetches and lays out, a hook named for two concerns, a `utils.ts` that has
become a drawer.

## Tests for new logic

Every branch this change adds is tested by this change: each arm of a new conditional in a hook
or handler; the loading, error and empty states of any new data-fetching component; both sides of
every changed threshold; a test that **fails without the fix** for every bug fix. Assert rendered
behaviour rather than implementation details, and intercept with MSW at the network boundary
rather than mocking the client module — see *Data access*.

## Theming

- Components reference design tokens. A literal colour in a component is a bug
- Tokens are CSS custom properties declared in both themes and republished to Tailwind with
  `@theme inline`. Light and dark are both implemented **from day one** — retrofitting dark
  onto a light-only system means finding every hardcoded surface again, which is a
  re-authoring rather than a change
- Contrast meets WCAG 2.1 AA in **both** themes. Dark is where it quietly fails: a muted
  foreground that passes on white rarely passes on near-black
- No class, token or folder is named after a product, project or codename. Names outlive the
  thing they were named for

## Data access

- Every response is parsed with Zod at the client boundary. A backend contract change should
  surface as a typed error, not as `undefined` deep inside a component
- One error shape across the app, so every caller handles failure the same way
- `staleTime` is set deliberately per query. One global default across a dashboard is a
  decision nobody made
- **The browser calls a same-origin path** (`/api/...`), proxied server-side. It never calls
  a backend origin directly — that is what keeps the backend URL, and any credential needed
  to reach it, out of the bundle

## Configuration and secrets

- **Nothing secret reaches the browser.** No API key, model key or service credential in
  source, in a `VITE_*` var, or anywhere in `dist/`. Grep the build output before believing
  otherwise — `VITE_*` values are inlined at build time and are readable by anyone with the page
- Tokens live in memory or an httpOnly cookie. Never `localStorage`, which any XSS can read
- URLs and feature flags come from configuration, never a literal in a component
- **The serving process exits at startup when required configuration is missing.** A server
  that starts and then 500s on first use has converted a deploy-time failure into a
  user-facing one
- No `dangerouslySetInnerHTML` without escape-then-allowlist sanitising

## Performance

- Route-level code splitting with `React.lazy` + `Suspense`; a page pulls in only its own code
- Memoise only where a profiler shows a cost. `useMemo` on trivial values is noise
- Virtualise any list that can exceed a few hundred rows
- Stable `key` from a domain id, never the array index, for any list that can reorder
- A bundle-size budget is enforced in CI as a failing check, not a warning

## Accessibility

- Semantic HTML; ARIA only where it fills a genuine gap
- Every interactive element is keyboard reachable with a visible focus ring. Removing the
  focus ring fails WCAG 2.1 AA and makes the app unusable by keyboard
- Overlays trap focus, close on `Escape`, and restore focus on close
- Every form control has an associated label
- `eslint-plugin-jsx-a11y` findings are **errors**. A rule nobody's build fails on is a
  preference, not a standard

## Gen AI UI patterns (when building AI features)

- Stream tokens as they arrive — never wait for the full response. Nothing in the path
  (including the server-side proxy) may buffer the stream
- Skeleton loaders for AI response areas, not spinners
- Every stream is cancellable — an `AbortController` wired to unmount **and** to a stop control
- Render model output as text or through a sanitising markdown renderer, never as raw HTML
- Show the grounding: cite the sources a RAG answer used, and say plainly when there are
  none. Confidence comes from the backend, not from the UI's own guess
- Label AI-generated content

## Code output per task — in this order

1. Zod schemas / TypeScript interfaces for the API response types
2. API client function — typed, with the shared error shape
3. Custom hook — data fetching + state
4. Component(s) — with loading, error and empty states
5. Tests (Vitest + RTL, API interactions through MSW handlers)
6. Accessibility notes for any non-standard interaction

## Quality rules

- No `any`. Use `unknown` and narrow, or define the interface
- Forms validate on submit **and** show inline errors on blur
- No hardcoded user-facing strings — a constants file or i18n keys
- Tests are co-located, exercise API interactions through MSW rather than by mocking the
  client module, and cover render, interaction, loading, error and empty
- The registry contract is tested: registered features appear in nav, live features route,
  roadmap features do not

## Acceptance criteria check

Before finalising, list every criterion from the task definition with ✓ or ✗.
Fix any ✗ before responding.

---

## Conformance

The audit checklist for this guideline lives beside it, in [`conformance/react.md`](conformance/react.md) — one file, one source of truth, loaded by whoever is auditing rather than by everyone who edits a file.
