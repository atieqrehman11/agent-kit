# React — conformance checklist

The audit list for [`react`](react.md). Walked by a reviewer, by the delivery gates, and by anyone auditing an existing front end.

This is payload, not a guideline: it carries no frontmatter and is never invocable. It lives apart from the rules so that whoever is *writing* code loads the rules without the checklist, and whoever is *auditing* loads the checklist without the rules. Every item below is defined in `react.md` — read it there when a check needs interpreting.

---

Stack:

- [ ] React 19, TypeScript `strict`, no `any`.
- [ ] Tailwind v4 with CSS-first `@theme`; no `tailwind.config.js`.
- [ ] Dialogs, dropdowns, comboboxes, tabs, tooltips and command palettes come from shadcn/ui, not hand-rolled.
- [ ] Data grids use TanStack Table; no bespoke sort/filter/paginate logic.
- [ ] Server state is TanStack Query. No `useEffect` fetch-and-store.
- [ ] No global store unless a feature demonstrably needs one.
- [ ] HTTP goes through one typed `fetch` client. No Axios.
- [ ] Prettier and `eslint-plugin-jsx-a11y` are configured, and a11y findings fail the build.

Shell and features:

- [ ] One feature registry drives both navigation and routing.
- [ ] Adding a feature required no edit to a shell file.
- [ ] Roadmap (`soon`) features register no route; their URLs reach the 404 surface.
- [ ] Every feature component is `React.lazy`, so each is its own chunk.
- [ ] No feature imports another feature, and `no-restricted-imports` enforces it.
- [ ] A feature's own files are reached by relative path, not by its own alias.
- [ ] An error boundary wraps the feature slot.

Theming:

- [ ] Components reference design tokens; no literal colours.
- [ ] Tokens are CSS custom properties bound to Tailwind with `@theme inline`.
- [ ] Light and dark are both implemented.
- [ ] No class, token or folder is named after a product, project or codename.

Data access:

- [ ] Every response is parsed with Zod. No `as T` on a fetch result.
- [ ] One error shape across the app.
- [ ] `staleTime` is set deliberately per query, not left at one global default.
- [ ] Components contain no fetching, business rules, or derived-state maths in JSX.
- [ ] The browser calls a same-origin path, proxied server-side — not a backend origin directly.

Configuration and secrets:

- [ ] No secret in any `VITE_*` var, in source, or anywhere in the built bundle.
- [ ] Grep the build output: no backend host, key or credential appears in `dist/`.
- [ ] Tokens are held in memory or an httpOnly cookie, never `localStorage`.
- [ ] URLs and feature flags come from configuration, never a literal in a component.
- [ ] The serving process exits at startup when required configuration is missing.
- [ ] No `dangerouslySetInnerHTML` without escape-then-allowlist sanitising.

Accessibility:

- [ ] Semantic HTML; ARIA only where it fills a genuine gap.
- [ ] Every interactive element is keyboard reachable with a visible focus ring.
- [ ] Overlays trap focus, close on `Escape`, and restore focus on close.
- [ ] Contrast meets WCAG 2.1 AA in **both** themes.
- [ ] Every form control has an associated label.

Performance:

- [ ] Route-level code splitting is in place.
- [ ] Lists that can exceed a few hundred rows are virtualised.
- [ ] List `key` comes from a domain id, never the array index.
- [ ] A bundle-size budget is enforced in CI as a failing check.

States:

- [ ] Every data-fetching component handles loading, error **and** empty.
- [ ] An empty result renders as empty, not as an error.

Testing:

- [ ] Tests are co-located with the components they cover.
- [ ] API interactions are exercised through MSW, not by mocking the client module.
- [ ] Each data-fetching component is tested for render, interaction, loading, error and empty.
- [ ] The registry contract is tested: registered features appear in nav, live features route, roadmap features do not.

If the feature streams model output:

- [ ] Tokens render as they arrive; no proxy in the path buffers the stream.
- [ ] An `AbortController` is wired to unmount and to a user-facing stop control.
- [ ] Model output renders as text or sanitised markdown, never as raw HTML.
- [ ] Sources are cited, absence of sources is stated plainly, and confidence comes from the backend.
- [ ] AI-generated content is labelled.

---
