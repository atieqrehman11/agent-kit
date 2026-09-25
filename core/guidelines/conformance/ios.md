# iOS — conformance checklist

The audit list for [`ios`](../ios.md). Walked by a reviewer, by the delivery gates, and by anyone auditing an existing native app.

This is payload, not a guideline: it carries no frontmatter and is never invocable. It lives apart from the rules so that whoever is *writing* code loads the rules without the checklist, and whoever is *auditing* loads the checklist without the rules. Every item below is defined in `ios.md` — read it there when a check needs interpreting.

Two tiers. **Per diff** is what a change can break — walk it every review. **Repo setup** is
settled once; audit it when the repo is new or the tooling changed, not on every feature.

---

## Per diff

Structure and naming:

- [ ] No feature imports another feature; a type used by two features moved to `Shared` in this MR, not ahead of a second caller.
- [ ] Views end in `View`, state holders in `Model` (not `ViewModel`/`Store`), repositories in `Repository`, services in `Service`.
- [ ] Booleans read as assertions (`isSyncing`, `canSubmit`).

State and concurrency:

- [ ] The app's one state-holder pattern (`@Observable` or `ObservableObject`/`@Published`) is used consistently — no mixing.
- [ ] State holders are `@MainActor`; no `DispatchQueue`, completion handler or semaphore in new code.
- [ ] Every `Task` started outside `.task {}` has a defined cancellation path.

Views:

- [ ] View bodies hold layout and bindings only — no networking, persistence, business rules, or formatting logic.
- [ ] No `AnyView` without a stated reason; bodies over ~60 lines or 2+ nested conditionals are split into subviews.
- [ ] Empty, loading and failed states are each rendered explicitly.

External-system boundary:

- [ ] The boundary is reached only through a repository; no View, Model or Service builds a request to it directly.
- [ ] The repository's public surface is domain types, not wire payloads.
- [ ] Every external call is behind a protocol with a fake, exercised in tests.
- [ ] Any write that auto-populates a system-of-record value carries a confidence signal and a user-visible confirmation before commit.

Offline (where the feature requires it):

- [ ] Mutations write to a durable outbox first; the UI reflects local truth without blocking on network.
- [ ] Mutations carry an idempotency key.
- [ ] Conflict policy for the entity is stated explicitly, not left to a global default.

Capture and on-device ML:

- [ ] Camera/media capture is behind a `Core` protocol; permission requests carry a purpose string reviewed as user-facing copy.
- [ ] On-device model inferences are versioned and recorded with their output.
- [ ] A no-model / low-confidence / offline path leaves the user a manual route, not a dead end.

Theming and accessibility:

- [ ] No literal colour, font, spacing or corner radius outside `Core/DesignSystem`.
- [ ] Dark mode and Dynamic Type (to `AX5`) are both implemented for anything this diff touches.
- [ ] Touch targets meet the 44pt minimum; every interactive element has an accessibility label.

Configuration and secrets:

- [ ] No secret in the repo, `Info.plist`, or `.xcconfig`; secrets come from build-time injection or Keychain, never `UserDefaults`.
- [ ] No endpoint, threshold, model name, retry count or timeout as a literal at a callsite.
- [ ] Any new ATS exception states its reason in the MR.
- [ ] No PII, user identity, physical address, or file path revealing captured user data in logs.

Quality:

- [ ] No force unwrap, `try!`, or `as!` in production code; no `fatalError` on a reachable path.
- [ ] Errors surface through the one typed error hierarchy — no raw `NSError`/transport error reaches a View.
- [ ] No commented-out code; no `TODO` without a ticket id.

Testing:

- [ ] Every service, repository and state holder touched has unit tests; views are tested through their model.
- [ ] A bug fix ships with the test that reproduces it.
- [ ] Repository fakes are the test seam — no test reaches a live external system.

## Repo setup — audit once, not per diff

- [ ] Swift 6, language mode 6, strict concurrency checking on (not `minimal`/`targeted`).
- [ ] SwiftUI for product surfaces; UIKit interop wrapped behind `UIViewRepresentable` at the edge only.
- [ ] Swift Package Manager only — no CocoaPods, no Carthage.
- [ ] Swift Testing for unit tests; XCTest reserved for UI tests.
- [ ] `.xcodeproj` is generated via XcodeGen (`project.yml`), not committed.
- [ ] Deployment target is a confirmed, stated decision — not inherited unexamined from scaffolding.
- [ ] Warnings are errors in CI; `SwiftLint` and `swift-format` both run in CI, not just locally.
- [ ] Every dependency in the manifest has a stated reason recorded somewhere durable (MR history at minimum).
