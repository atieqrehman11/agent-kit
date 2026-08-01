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
- Custom hooks for all business logic: useDocumentUpload, useAnomalyList, etc.
- Co-locate: Component.tsx + Component.test.tsx in the same directory
- Error boundaries at page level minimum
- Loading, error, and empty states are mandatory for every data-fetching component
- Accessibility: semantic HTML, ARIA labels on interactive elements, keyboard nav

## Folder structure per feature

src/features/[feature-name]/
  components/    UI components
  hooks/         Custom hooks (data fetching + state)
  api/           API call functions (typed with Zod schemas)
  store/         Zustand slice (if feature has global state)
  types/         TypeScript interfaces
  index.ts       Public exports

## Gen AI UI patterns (when building AI features)

- Streaming responses: use EventSource or fetch with ReadableStream
- Display tokens as they arrive — never wait for full response
- Skeleton loaders for AI response areas, not spinners
- Retry UI with exponential backoff messaging
- Clearly label AI-generated content in the UI

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
