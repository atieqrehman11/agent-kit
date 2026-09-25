---
name: ios
kind: guideline
description: >
  Standards for native iOS apps: tech stack, the app/feature split, state and concurrency,
  the external-system boundary, offline support, capture and on-device ML, theming,
  accessibility, and testing. Applies whenever Swift, SwiftUI or Xcode project
  configuration is written, changed or reviewed.
applies_to:
  - "**/*.swift"
  - "**/*.xcconfig"
  - "**/project.yml"
  - "**/Package.swift"
  - "**/*.xcodeproj/**"
  - "**/Info.plist"
---

# iOS — standards

You are a senior Swift/SwiftUI developer. Implement to production quality.

The audit list for these rules is [`conformance/ios.md`](conformance/ios.md).

This guideline covers **how the app is built**. It does not own the visual language — colour,
type and spacing tokens live wherever the project's own design-system skill or guide puts
them; this file only requires that they live *somewhere* named, not inline.

Layering, error handling and configuration rules come from the `service-structure` guideline
and are not restated here; where this file names a boundary, that guideline defines what the
boundary may not do.

## Tech stack

- **Swift 6**, language mode 6, **strict concurrency checking on** — not `minimal`, not
  `targeted`. Data-race safety is a compile-time guarantee or it is not a guarantee.
- **SwiftUI** for all product surfaces. UIKit only where SwiftUI genuinely lacks the
  capability (camera preview, some `AVFoundation` interop) and then wrapped behind a
  `UIViewRepresentable` at the edge, never leaked into feature code.
- **Swift Package Manager** for dependencies. No CocoaPods, no Carthage.
- **Swift Testing** (`import Testing`, `@Test`, `#expect`) for unit tests. XCTest only for
  UI tests, which still require it.
- **XcodeGen** (`project.yml`) so the `.xcodeproj` is generated, not committed. A merge
  conflict inside a project file is not a reviewable diff.
- Deployment target is a stated project decision, not a default — confirm it against the
  actual device fleet or App Store minimums rather than assuming it's still correct because
  it's already configured. It also decides the state-holder pattern below.
- Dependencies are a liability on a device fleet you do not fully control. Each one needs a
  stated reason in the MR that adds it.

## App and features

```
Sources/
  App/                 App entry, root navigation, DI composition root, theme setup
  Core/
    DesignSystem/      Tokens, primitives, modifiers — the only place raw values appear
    Networking/        Transport, auth, retry — no endpoint knowledge
    Persistence/       Local store, the outbox (if offline support is required), migrations
    Sync/              The reconciliation engine (if offline support is required)
  Features/
    <Feature>/
      Views/           SwiftUI views — layout and binding only
      <Feature>Model   State holder
      Services/        Use-case logic
      Repositories/    The boundary to any backend or external system
      Models/          Domain types for this feature
  Shared/              Cross-feature types with a stated reason to be shared
Tests/
  <Feature>Tests/
```

- A feature may depend on `Core` and `Shared`. **A feature may never import another
  feature.** If two features need the same thing, it moves to `Shared` in the same MR.
- `Shared` is where things go after a second caller exists, not in anticipation of one.

### Naming

- Types `UpperCamelCase`, members `lowerCamelCase` — no abbreviations except the ones
  Apple's own APIs use (`URL`, `ID`).
- Views end in `View` (`JobListView`). State holders end in `Model` (`JobListModel`) — not
  `ViewModel`, not `Store`.
- Repositories end in `Repository`, services in `Service`.
- Booleans read as assertions: `isSyncing`, `hasPendingUpload`, `canSubmit`.
- Test names say the behaviour, not the method: `submitsQueuedItemOnceNetworkReturns`.

## State and concurrency

- Choose **one** state-holder pattern for the whole app and do not mix them: `@Observable`
  if the deployment target is iOS 17+, otherwise `ObservableObject` with `@Published` (the
  Observation framework behind `@Observable` requires iOS 17+ and will not compile against
  an older target). Revisit only if the deployment target moves.
- `@StateObject` owns (the view that creates the instance), `@ObservedObject` lends (passed
  in from a parent), `@EnvironmentObject` reaches for app-wide services injected via
  `.environmentObject()`. Nothing else. (Substitute `@State`/environment values if the app
  uses `@Observable`.)
- **All UI state is `@MainActor`.** Annotate the state holder, not individual methods.
- Use structured concurrency — `async`/`await`, `TaskGroup`, `.task {}` on views.
  **No `DispatchQueue`, no completion handlers, no semaphores** in new code.
- Long-running work belongs in an `actor`, not a main-actor class with a background queue.
- Every `Task` started outside `.task {}` must have a defined cancellation path. An orphaned
  `Task` that writes after the user left the screen is a data bug.

## Views

- A `View` body holds **layout and bindings only**. No networking, no persistence, no
  business rules, no date/number formatting logic.
- Body over ~60 lines, or more than 2 levels of nested conditionals: extract a subview.
- Extract subviews as `struct`s, not `@ViewBuilder var` soup — a struct gets its own
  identity and its own invalidation scope.
- No `AnyView` unless type erasure is genuinely required; it defeats the diffing.
- Every view that can be empty, loading, or failed renders all three states explicitly.
  "Nothing on screen" is not a loading state.

## The external-system boundary

Any backend or third-party system this app talks to is reached the same way a service-layer
boundary is reached anywhere else — see `service-structure`:

- It is reached **only** through a repository type. A View, a Model, or a Service never
  constructs a request to it directly.
- The repository exposes **domain types, not wire payloads.** No transport field name,
  label, or JSON shape crosses out of the repository layer.
- Every call to it is behind a protocol with a fake implementation, so features are
  testable and demoable with no live backend.
- If a write can auto-populate a value a human would otherwise enter into a system of
  record, treat a wrong value as worse than no value: carry a confidence signal and require
  a user-visible confirmation before the write commits.

## Offline support

Where the app must work offline — state this as a per-feature decision, not an assumption:

- **Every mutation is written locally first**, to a durable outbox, then synced. The UI
  reflects local truth immediately and never blocks on the network.
- The outbox survives app termination and device restart. In-memory queues do not count.
- Mutations carry an **idempotency key** so a retry after an ambiguous failure cannot
  double-post.
- Conflict policy is **explicit per entity** and written down — last-write-wins, merge, or
  user-resolves. There is no global default.
- Sync state is visible to the user, and for any UI that may be read under poor contrast or
  glare, encode it with more than colour alone (icon plus shape).
- Media captured for later upload is written to disk and referenced by path. Never hold it
  in memory awaiting upload.

## Capture and on-device ML

- Camera and media capture live in `Core`, behind a protocol. Features request a capture
  and receive a file reference.
- Request the narrowest permission that works, at the moment it is needed, with a purpose
  string that says what the user gets. Every `NS*UsageDescription` is user-facing copy and
  is reviewed as such.
- Any on-device model is **versioned and recorded with its output.** A stored inference that
  cannot be traced to a model version cannot be evaluated later.
- An accuracy claim needs a labelled benchmark, not vibes; report precision and recall
  separately rather than a single "accuracy" number when the write matters.
- Degrade, do not fail: no model, no network, or a low-confidence result must leave the user
  with a manual path, not a dead end.

## Theming and design system

- **No literal colours, fonts, spacings or corner radii outside `Core/DesignSystem`.** Not
  one. A hex value in a feature file is a review block.
- **Dark mode is supported**, not deferred — every colour is defined for both appearances in
  the asset catalog.
- **Dynamic Type is supported to the accessibility sizes.** Test at `AX5`. No fixed-height
  containers around text.
- Contrast meets WCAG AA at minimum.

## Accessibility

- **Touch targets meet the 44pt minimum**, with no dense tap clusters.
- Every interactive element has an accessibility label; every image conveying state has a
  trait. VoiceOver order is checked, not assumed.
- Respect Reduce Motion.
- If a flow has a companion **watchOS** target, design its degraded (glanceable) form
  alongside the phone flow, not after it.

## Configuration and secrets

- Build settings in **`.xcconfig` files**, one per configuration. No build settings edited
  in the Xcode UI — they land in the project file and vanish on regeneration.
- **No secret in the repo, in `Info.plist`, or in an `.xcconfig`.** Injected at build time or
  fetched at runtime; stored in **Keychain**, never `UserDefaults`.
- No endpoint, threshold, model name, retry count or timeout as a literal at a callsite.
- App Transport Security stays on. An ATS exception needs a stated reason in the MR.
- **No PII, user identity, physical address, or file path that reveals captured user data
  (e.g. a photo or recording path) in logs.** Log levels come from configuration, not from
  code edits.

## Tests

- Every service, repository and state holder has unit tests. Views are tested through their
  model, not by snapshotting layout.
- Test the failure states that actually happen: offline, flapping connectivity, ambiguous
  write failure, app killed mid-sync (where offline support applies), permission denied,
  storage full.
- Repository fakes are the default test seam; no test reaches a live external system.
- UI tests cover the critical path only.
- A bug fix lands with the test that reproduces it.

## Code output per task — in this order

1. Domain models and protocols
2. Repository (plus its fake)
3. Service / use-case logic
4. State holder
5. Views
6. Tests
7. Wiring into the composition root

## Quality rules

- No force unwrap (`!`), no `try!`, no `as!` in production code. Tests may force-unwrap.
- No `fatalError` on a path a user can reach.
- Warnings are errors in CI. `SwiftLint` and `swift-format` run in CI, not just locally.
- Errors surface as one typed error hierarchy behind one boundary handler — see
  `service-structure`. A raw `NSError` or transport error never reaches a View.
- An error shown to a user says what to do next. "Request failed" does not.
- No commented-out code, no `TODO` without a ticket id.
