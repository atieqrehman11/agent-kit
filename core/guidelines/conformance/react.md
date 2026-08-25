# React — conformance checklist

The audit list for [`react`](../react.md). Walked by a reviewer, by the delivery gates, and by anyone auditing an existing front end.

This is payload, not a guideline: it carries no frontmatter and is never invocable. It lives apart from the rules so that whoever is *writing* code loads the rules without the checklist, and whoever is *auditing* loads the checklist without the rules. Every item below is defined in `react.md` — read it there when a check needs interpreting.

Two tiers. **Per diff** is what a change can break — walk it every review. **Repo setup** is
settled once; audit it when the repo is new or the tooling changed, not on every feature.

---

## Per diff

Components and complexity:

- [ ] No function added or changed exceeds complexity **10**, nesting depth **4**, **50** statements or **5** parameters.
- [ ] JSX nesting stays within depth **4**, and no conditional branch is a nested ternary inside JSX.
- [ ] Every `// eslint-disable` for a complexity rule carries a comment giving the reason.
- [ ] Components render and hooks decide — no fetch, business rule or derived-state maths in JSX.
- [ ] No component both fetches and lays out; no hook is named for two concerns; components over ~150 lines were examined for a hook-shaped seam.

Naming:

- [ ] Every file and folder added is `kebab-case` — including a file holding a single component.
- [ ] Component and type exports are `PascalCase`; functions and hooks `camelCase`; constants `SCREAMING_SNAKE_CASE`.
- [ ] A test sits beside its subject under the same stem (`thing-card.tsx` / `thing-card.test.tsx`).

States:

- [ ] Every data-fetching component handles loading, error **and** empty.
- [ ] An empty result renders as empty, not as an error.

Data access:

- [ ] Every response is parsed with Zod. No `as T` on a fetch result.
- [ ] One error shape across the app, and `staleTime` is set deliberately per query.
- [ ] The browser calls a same-origin path, proxied server-side — not a backend origin directly.

Secrets and configuration:

- [ ] No secret, backend host or credential in a `VITE_*` var, in source, or in the built `dist/` — grep the output rather than assuming.
- [ ] Tokens are held in memory or an httpOnly cookie, never `localStorage`.
- [ ] URLs and feature flags come from configuration, never a literal in a component.
- [ ] No `dangerouslySetInnerHTML` without escape-then-allowlist sanitising.

Theming:

- [ ] Components reference design tokens; no literal colours.
- [ ] Light and dark are both implemented, and contrast meets WCAG 2.1 AA in **both**.
- [ ] No class, token or folder is named after a product, project or codename.

Accessibility:

- [ ] Semantic HTML; ARIA only where it fills a genuine gap.
- [ ] Every interactive element is keyboard reachable with a visible focus ring, and every form control has a label.
- [ ] Overlays trap focus, close on `Escape`, and restore focus on close.

Performance:

- [ ] Lists that can exceed a few hundred rows are virtualised.
- [ ] List `key` comes from a domain id, never the array index.

Testing:

- [ ] Tests are co-located, and API interactions go through MSW rather than mocking the client module.
- [ ] Each data-fetching component is tested for render, interaction, loading, error and empty.
- [ ] Every conditional this diff adds to a hook or handler has a test per arm, and every changed threshold is tested on both sides.
- [ ] Every bug fix ships a test that fails without the fix.
- [ ] Tests assert rendered behaviour, not implementation details.

## Repo setup — audit once, not per diff

- [ ] React 19 + TypeScript `strict` with no `any`; Tailwind v4 CSS-first `@theme` and no `tailwind.config.js`.
- [ ] Behavioural components (dialogs, dropdowns, comboboxes, tabs, tooltips, command palettes) come from shadcn/ui; grids from TanStack Table; server state from TanStack Query with no `useEffect` fetch-and-store; one typed `fetch` client and no Axios; no global store by default.
- [ ] One feature registry drives both nav and routing, adding a feature needs no shell edit, and roadmap (`soon`) features register no route.
- [ ] Every feature is `React.lazy`; no feature imports another (`no-restricted-imports` enforces it); an error boundary wraps the feature slot.
- [ ] The registry contract is tested: registered features appear in nav, live features route, roadmap features do not.
- [ ] Complexity rules are `error` not `warn`; `eslint-plugin-jsx-a11y` findings fail the build; a bundle-size budget is a failing CI check; route-level code splitting is in place.
- [ ] The serving process exits at startup when required configuration is missing.

## If the feature streams model output

- [ ] Tokens render as they arrive; no proxy in the path buffers the stream.
- [ ] An `AbortController` is wired to unmount and to a user-facing stop control.
- [ ] Model output renders as text or sanitised markdown, never as raw HTML.
- [ ] Sources are cited, absence of sources is stated plainly, and confidence comes from the backend.
- [ ] AI-generated content is labelled.

---
