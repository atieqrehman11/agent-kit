---
name: android
kind: guideline
description: >
  Standards for native Android apps: tech stack, the module/feature split, state and
  concurrency, the external-system boundary, offline support, background work, capture and
  on-device ML, theming, accessibility, performance and testing. Applies whenever Kotlin,
  Jetpack Compose or Gradle/Android project configuration is written, changed or reviewed.
applies_to:
  - "**/*.kt"
  - "**/*.kts"
  - "**/AndroidManifest.xml"
  - "**/libs.versions.toml"
  - "**/gradle.properties"
  - "**/proguard-rules.pro"
  - "**/detekt.yml"
---

# Android — standards

You are a senior Kotlin/Jetpack Compose developer. Implement to production quality.

The audit list for these rules is [`conformance/android.md`](conformance/android.md).

This guideline covers **how the app is built**. It does not own the visual language — colour,
type and spacing tokens live wherever the project's own design-system skill or guide puts
them; this file only requires that they live *somewhere* named, not inline.

Layering, error handling and configuration rules come from the `service-structure` guideline
and are not restated here; where this file names a boundary, that guideline defines what the
boundary may not do.

It deliberately mirrors the shape of the `ios` guideline — same layers, same boundaries, same
ordering of work — so a team shipping both platforms reviews them the same way. Where Android
differs because the platform differs (process death, the manifest, OEM battery management),
the difference is stated rather than hidden behind a shared name.

## Tech stack

- **Kotlin 2.x**, with `allWarningsAsErrors` on. **K2 compiler**; no new Java source.
- **Jetpack Compose** (Material 3 as the base layer, wrapped by the app's own design system)
  for all product surfaces. The View system only where Compose genuinely lacks the capability
  (camera preview via `PreviewView`, some `WebView` interop) and then wrapped in
  `AndroidView` at the edge, never leaked into feature code.
- **Gradle Kotlin DSL** with a **version catalog** (`gradle/libs.versions.toml`) and
  **convention plugins** in `build-logic/`. No version literal in a module's `build.gradle.kts`.
- **Coroutines and `Flow`** for all asynchrony. No RxJava, no `AsyncTask`, no callbacks in new
  code.
- **Hilt** (KSP, not kapt) for dependency injection. The composition root is the `:app`
  module; nothing else knows the concrete graph.
- **Room** for structured local data, **DataStore** for preferences, **WorkManager** for
  deferrable guaranteed work (the outbox drain, uploads). No `SharedPreferences`, no raw
  `SQLiteOpenHelper`.
- **OkHttp + Retrofit** with **kotlinx.serialization** for transport. Nothing else parses JSON.
- **Navigation Compose**, type-safe routes (serializable route objects, not string patterns).
- **Unit tests:** JUnit 5 + **Turbine** for `Flow`, **fakes over mocks**. Compose UI tests and
  instrumented tests stay on JUnit 4 because the Android runner requires it.
- **Quality tooling:** **Detekt** and **ktlint** (via Spotless), plus Android Lint with
  `warningsAsErrors true`. All three run in CI.
- **minSdk is a stated project decision, not a default** — confirm it against the real device
  fleet (including managed/rugged devices and their OS update policy) rather than assuming the
  scaffolded value is still correct. `targetSdk` follows the Play Store requirement and is
  moved deliberately, with the behaviour-change notes read, not bumped to silence a warning.
- Dependencies are a liability on a device fleet you do not fully control. Each one needs a
  stated reason in the MR that adds it. Prefer AndroidX and first-party libraries.

## Modules and features

One Gradle module per feature, so "a feature may never import another feature" is enforced by
the build, not by code review.

```
app/                       Application class, root navigation, Hilt graph, manifest, theme setup
build-logic/               Convention plugins — the only place build config is shared
core/
  designsystem/            Tokens, primitives, modifiers — the only place raw values appear
  network/                 Transport, auth, retry — no endpoint knowledge
  database/                Room, the outbox (if offline support is required), migrations
  sync/                    The reconciliation engine and its WorkManager workers
  common/                  Result types, error hierarchy, dispatchers, logging interface
feature/
  <feature>/
    ui/                    Composables — layout and binding only
    <Feature>ViewModel     State holder
    domain/                Use-case logic, domain types
    data/                  Repository implementations — the boundary to any backend
shared/                    Cross-feature types with a stated reason to be shared
```

- A feature module may depend on `core:*` and `shared`. **A feature may never depend on
  another feature module.** If two features need the same thing, it moves to `shared` in the
  same MR. Navigation between features goes through route types owned by `app` or `shared`.
- `shared` is where things go after a second caller exists, not in anticipation of one.
- Within a module, use `internal` by default. Only the module's public contract — the
  repository interface, the route, the entry composable — is `public`. Enable explicit API
  mode on `core:*` and `shared`.
- The dependency direction is `app → feature → core`. `core` never depends on `feature`.

### Naming

- Types `UpperCamelCase`, members `lowerCamelCase`, constants `SCREAMING_SNAKE_CASE`. No
  abbreviations except those the platform uses (`Url`, `Id`).
- **Deliberate divergence from iOS:** the state holder is an AndroidX `ViewModel`, so it ends in
  `ViewModel` (`JobListViewModel`). The platform type is named that way and every Android
  developer looks for it by that name; renaming it to match iOS buys nothing.
- Screens end in `Screen` (`JobListScreen`) — the composable bound to a route. Smaller
  composables are named for what they show (`JobCard`), not `JobCardView`.
- Repositories end in `Repository`, use cases in `UseCase` (one public `operator fun invoke`).
- UI state is a single `<Feature>UiState`; user input is a sealed `<Feature>Action`; one-off
  effects (navigation, snackbar) are a sealed `<Feature>Effect`.
- Booleans read as assertions: `isSyncing`, `hasPendingUpload`, `canSubmit`.
- Test names say the behaviour, not the method: `submitsQueuedItemOnceNetworkReturns`.

## State and concurrency

- State flows **one way**: the ViewModel exposes a single immutable `StateFlow<UiState>`;
  the UI sends `Action`s back. A composable never mutates state it was handed.
- Collect with **`collectAsStateWithLifecycle()`**, never bare `collectAsState()` — collection
  must stop when the app is not visible.
- **Expose `StateFlow` built with `stateIn(viewModelScope, WhileSubscribed(5_000), initial)`**,
  not a public `MutableStateFlow`. `MutableStateFlow` is private to the ViewModel.
- `UiState` is a `data class` or sealed interface of **immutable** fields. Use
  `kotlinx.collections.immutable` (`ImmutableList`) for lists passed into composables so
  Compose can skip recomposition.
- **Survive process death.** The OS kills a backgrounded app without warning. State the user
  would be angry to lose (a half-filled form, a selected job) goes through `SavedStateHandle`
  or is persisted to Room; it never lives only in a ViewModel field.
- **One-off effects are a `Channel` collected in a `LaunchedEffect`, or are modelled as state
  that the UI acknowledges.** Never a `SharedFlow` with `replay = 0` that drops events when
  nothing is collecting.
- **Inject dispatchers** (`IoDispatcher`, `DefaultDispatcher`) — never write `Dispatchers.IO`
  at a call site. Tests replace them.
- **Structured concurrency only.** Work launches from `viewModelScope`, a `CoroutineScope`
  with a defined lifetime, or WorkManager. **No `GlobalScope`.** No `runBlocking` outside tests
  and `main`. Never `catch (e: Exception)` around a suspend call without rethrowing
  `CancellationException`.
- Long-lived work that must outlive the screen belongs in a WorkManager worker or a foreground
  service (see Background work), not a coroutine in a ViewModel.
- Every `launch` outside `viewModelScope`/`rememberCoroutineScope` has a defined cancellation
  path. An orphaned coroutine that writes after the user left the screen is a data bug.

## Composables

- A composable holds **layout and bindings only**. No networking, no persistence, no business
  rules, no date/number formatting logic — formatting is done in the ViewModel or a formatter
  in `core:common`.
- **State hoisting.** A reusable composable takes state and lambdas and owns none. The
  `Screen` composable is the only one that touches the ViewModel; everything below receives
  plain values, which is what makes it previewable and testable.
- Body over ~60 lines, or more than 2 levels of nested conditionals: extract a composable.
- **Every composable takes a `modifier: Modifier = Modifier` as its first optional
  parameter**, applies it to its root, and never hard-codes size the caller should decide.
- **Stability matters.** Parameters are immutable or `@Immutable`/`@Stable`; lambdas passed
  into lists are remembered or hoisted; keys are supplied for `LazyColumn` items
  (`key = { it.id }`). Do not allocate in composition (`remember` it, or compute it in the
  ViewModel).
- Use `derivedStateOf` for state derived from fast-changing state; read state as late as
  possible (pass a lambda, not a value) so a fast-changing value does not recompose a whole
  subtree.
- Side effects live in effect handlers (`LaunchedEffect`, `DisposableEffect`) with correct
  keys. No side effect in the composable body.
- Every screen that can be empty, loading, or failed renders all three states explicitly.
  "Nothing on screen" is not a loading state.
- Every public composable has a `@Preview` for each of its states, in light and dark.
- No `Modifier.composed {}` in new code — use `Modifier.Node`.

## The external-system boundary

Any backend or third-party system this app talks to is reached the same way a service-layer
boundary is reached anywhere else — see `service-structure`:

- It is reached **only** through a repository interface. A composable, a ViewModel or a use
  case never constructs a request to it directly, and `Retrofit`/`OkHttp` types never appear
  outside `data/`.
- The repository exposes **domain types, not wire payloads.** No DTO, transport field name,
  label, or JSON shape crosses out of the data layer. Mappers are explicit and tested.
- Every call to it is behind an interface with a fake implementation, so features are
  testable and demoable with no live backend. The Hilt graph can swap a fake in.
- Failures cross the boundary as a typed result or a sealed error — never as a raw
  `IOException` or `HttpException`.
- If a write can auto-populate a value a human would otherwise enter into a system of
  record, treat a wrong value as worse than no value: carry a confidence signal and require
  a user-visible confirmation before the write commits.

## Offline support

Where the app must work offline — state this as a per-feature decision, not an assumption:

- **Every mutation is written locally first**, to a durable outbox in Room, then synced. The
  UI observes the database and reflects local truth immediately; it never blocks on the
  network.
- The outbox survives process death, app force-stop and device reboot. In-memory queues do
  not count. Draining runs as **unique WorkManager work** with a network constraint and
  exponential backoff.
- Mutations carry an **idempotency key** so a retry after an ambiguous failure cannot
  double-post.
- Conflict policy is **explicit per entity** and written down — last-write-wins, merge, or
  user-resolves. There is no global default.
- **Room is the single source of truth.** The UI reads from Room via `Flow`; the network only
  writes into Room. A screen that renders a network response directly is a review block.
- Every Room schema change is a **tested migration** with exported schemas committed.
  `fallbackToDestructiveMigration` is forbidden — it deletes unsynced technician data.
- Sync state is visible to the user, and for any UI that may be read under poor contrast or
  glare, encode it with more than colour alone (icon plus shape).
- Media captured for later upload is written to app-specific storage and referenced by path.
  Never hold it in memory awaiting upload, and never pass a `Bitmap` through navigation or a
  `SavedStateHandle`.

## Background work

The platform actively kills background work. Design for that, not against it.

- **Pick the narrowest mechanism that works:** WorkManager for deferrable guaranteed work; a
  **foreground service** only for user-visible ongoing work, declared with the correct
  `foregroundServiceType` and a persistent notification; `AlarmManager` exact alarms only for
  user-set reminders, and only with the permission policy checked.
- Never rely on a plain service, a long-running coroutine in a ViewModel, or `Handler` loops
  to keep work alive while the app is backgrounded.
- **Doze, App Standby Buckets and OEM battery managers** will delay or kill work. Assert the
  behaviour on a real device from each OEM in the fleet; do not assume the emulator is
  representative. Do not ask the user to exempt the app from battery optimisation unless the
  feature is impossible without it, and say why in the MR.
- Push is **Firebase Cloud Messaging**. Treat a push as a hint to sync, not as the data: the
  payload is small and may never arrive. Use data messages for sync triggers and notification
  messages only for user-visible alerts. Register the token with the backend and handle
  rotation.
- Create notification **channels** at startup, one per user-meaningful category, so a user can
  silence one thing without silencing everything. Request `POST_NOTIFICATIONS` at the moment it
  is needed.

## Capture and on-device ML

- Camera and media capture live in `core`, behind an interface, implemented with **CameraX**.
  Features request a capture and receive a file reference.
- Request the narrowest permission that works, at the moment it is needed, with a rationale
  that says what the user gets. Every permission rationale string is user-facing copy and is
  reviewed as such. Handle "denied" and "denied permanently" as separate states, with a path
  to settings for the second.
- Prefer the **photo picker** and scoped storage over broad storage permissions. No
  `MANAGE_EXTERNAL_STORAGE`.
- Any on-device model is **versioned and recorded with its output.** A stored inference that
  cannot be traced to a model version cannot be evaluated later.
- An accuracy claim needs a labelled benchmark, not vibes; report precision and recall
  separately rather than a single "accuracy" number when the write matters.
- Degrade, do not fail: no model, no network, or a low-confidence result must leave the user
  with a manual path, not a dead end. Inference runs off the main thread and is cancellable.

## Theming and design system

- **No literal colours, fonts, `dp`/`sp` spacings or corner radii outside `core:designsystem`.**
  Not one. A hex value or a bare `16.dp` in a feature file is a review block.
- Expose tokens through a `CompositionLocal`-backed theme object; features read
  `AppTheme.colors.surface`, not `MaterialTheme.colorScheme.surface` directly, so the design
  system can change without touching features.
- **Dark theme is supported**, not deferred — every colour has a light and a dark value.
  Dynamic colour (Material You) is a deliberate on/off decision, not an accident of the
  default.
- **Font scale is supported to 200%.** Test at the largest system font size and at largest
  display size. Text is in `sp`; no fixed-height container around text.
- Contrast meets WCAG AA at minimum.
- **Edge-to-edge** is on and insets are handled explicitly (`WindowInsets`) — IME, status bar,
  navigation bar and display cutouts. Predictive back is supported.
- Use vector drawables or Compose `ImageVector`; no raster asset that has a vector source.

## Accessibility

- **Touch targets meet the 48dp minimum**, with no dense tap clusters. Use
  `Modifier.minimumInteractiveComponentSize()` rather than padding by eye.
- Every interactive element has a `contentDescription` or merged semantics; decorative images
  are explicitly `null`. State is exposed through semantics (`stateDescription`, `role`), not
  colour alone. **TalkBack order is checked, not assumed** — use `Modifier.semantics` and
  `traversalIndex` where the visual order misleads.
- Respect the system **animation scale / reduce motion** setting.
- Run the **Accessibility Scanner** and Compose accessibility checks in UI tests for each
  critical screen.
- If a flow has a companion **Wear OS** target, design its degraded (glanceable) form
  alongside the phone flow, not after it.

## Configuration and secrets

- Build settings live in **Gradle** (`buildTypes`, `productFlavors`) and **convention
  plugins**, with per-environment values in `BuildConfig` fields generated from properties —
  never hand-edited in a generated file.
- **No secret in the repo, in `strings.xml`, in `BuildConfig`, or in `local.properties`
  committed to source control.** Injected by CI at build time, or fetched at runtime. A secret
  compiled into the APK is public — assume the APK is decompiled.
- Tokens and credentials are stored with the **Android Keystore** (hardware-backed where
  available), never in `SharedPreferences`/`DataStore` in the clear. `EncryptedSharedPreferences`
  is deprecated; use DataStore with a Keystore-backed key (Tink).
- `android:allowBackup="false"` or an explicit `dataExtractionRules`/`fullBackupContent`
  allow-list — an unencrypted cloud backup of tokens and technician data is a leak.
- **Network security config stays on.** Cleartext traffic is disabled; a cleartext or
  user-CA exception needs a stated reason in the MR and is limited to debug builds.
- Every manifest component is `android:exported="false"` unless it must be reachable, and an
  exported one declares the permission or intent filter that justifies it. Deep links are
  validated as untrusted input.
- **Release builds are minified and shrunk (R8), with resource shrinking.** Keep rules are
  scoped to the library that needs them, not `-keep class **`. The release build is the one
  that gets tested before shipping, not just debug.
- No endpoint, threshold, model name, retry count or timeout as a literal at a callsite.
- **No PII, user identity, physical address, token, or file path that reveals captured user
  data in logs.** Use **Timber** (or the app's `Logger` interface) with a no-op tree in
  release; log levels come from configuration, not code edits. `Log.d` is banned by lint.

## Performance

"Optimised" is measured, not asserted.

- **Startup:** nothing blocking in `Application.onCreate`. Defer initialisation with
  **App Startup** or lazily; keep cold start within the budget the project states. Ship a
  **Baseline Profile** and generate it in CI.
- **Main thread:** no disk, network or heavy computation on it. **StrictMode** is enabled in
  debug builds, with `penaltyLog`/`penaltyDeath` for violations the project has decided to
  hold at zero.
- **Compose:** check recomposition counts for any screen with a list or animation (Layout
  Inspector); no allocation in a scroll path; `LazyColumn`/`LazyRow` for anything that is not
  a handful of fixed children; `contentType` set for heterogeneous lists.
- **Memory:** no `Context`/`Activity` reference held in a singleton or static; no `Bitmap`
  retained beyond its screen; images are sampled to display size (Coil, not manual decoding).
  **LeakCanary** runs in debug builds.
- **Battery and network:** batch and constrain background work; no polling where a push or a
  constrained worker will do; honour metered-network constraints for large uploads.
- **APK/AAB size:** ship an **App Bundle**; audit the dependency tree when size grows; a
  library that adds more than a stated budget needs justification in its MR.
- Performance claims in an MR cite a **Macrobenchmark**, a Perfetto trace or a profiler
  capture. "Feels faster" is not evidence.

## Tests

- Every use case, repository and ViewModel has unit tests. Composables are tested through
  their state (`createComposeRule` against a hoisted `UiState`), not by snapshotting layout.
- Test the failure states that actually happen: offline, flapping connectivity, ambiguous
  write failure, process death mid-sync, app force-stopped, permission denied (and
  permanently denied), storage full, Doze delaying a worker (where offline support applies).
- Repository fakes are the default test seam; no test reaches a live external system.
  Use `runTest` with injected dispatchers and `Turbine` for flows; no `Thread.sleep`, no real
  delay.
- **Room migrations are tested** against exported schemas (`MigrationTestHelper`).
- **WorkManager workers are tested** with `TestListenableWorkerBuilder` / `WorkManagerTestInitHelper`.
- UI/instrumented tests cover the critical path only, and run on a managed device or emulator
  in CI.
- A bug fix lands with the test that reproduces it.

## Code output per task — in this order

1. Domain models and interfaces
2. Repository (plus its fake)
3. Use case / domain logic
4. ViewModel (`UiState`, `Action`, `Effect`)
5. Composables and previews
6. Tests
7. Wiring into the Hilt graph and navigation

## Quality rules

- **No `!!`, no unchecked `as` cast, no `lateinit` on a type that can be constructor-injected**
  in production code. Tests may use `!!`.
- No `TODO()` / `error("…")` on a path a user can reach.
- **Warnings are errors in CI.** Detekt, ktlint and Android Lint all run in CI, not just
  locally, and a Lint baseline file may only shrink.
- Errors surface as one typed error hierarchy behind one boundary handler — see
  `service-structure`. A raw `Throwable` or transport exception never reaches a composable.
- An error shown to a user says what to do next. "Request failed" does not.
- No commented-out code, no `TODO` without a ticket id.
- Public API of a module is documented with KDoc; implementation comments say *why*, never
  *what*.
- Kotlin idiom: prefer `val` and immutable data; `sealed` hierarchies over flag booleans;
  `when` as an exhaustive expression with no `else` over a sealed type; scope functions for
  clarity, not nesting (no more than one level); expression bodies for single-expression
  functions; no platform types leaking from Java APIs without an explicit nullability.
