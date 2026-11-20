# Android — conformance checklist

The audit list for [`android`](../android.md). Walked by a reviewer, by the delivery gates, and by anyone auditing an existing native app.

This is payload, not a guideline: it carries no frontmatter and is never invocable. It lives apart from the rules so that whoever is *writing* code loads the rules without the checklist, and whoever is *auditing* loads the checklist without the rules. Every item below is defined in `android.md` — read it there when a check needs interpreting.

Two tiers. **Per diff** is what a change can break — walk it every review. **Repo setup** is
settled once; audit it when the repo is new or the tooling changed, not on every feature.

---

## Per diff

Structure and naming:

- [ ] No feature module depends on another feature module; a type used by two features moved to `shared` in this MR, not ahead of a second caller.
- [ ] `core` does not depend on `feature`; nothing outside the module's contract is `public`.
- [ ] Screens end in `Screen`, state holders in `ViewModel`, repositories in `Repository`, use cases in `UseCase`; state/action/effect are `UiState`/`Action`/`Effect`.
- [ ] Booleans read as assertions (`isSyncing`, `canSubmit`).

State and concurrency:

- [ ] Each ViewModel exposes one immutable `StateFlow<UiState>`; `MutableStateFlow` is private.
- [ ] UI collects with `collectAsStateWithLifecycle()`, not `collectAsState()`.
- [ ] State the user would be upset to lose survives process death (`SavedStateHandle` or Room).
- [ ] One-off effects use a `Channel` or acknowledged state — no `SharedFlow(replay = 0)` that can drop events.
- [ ] Dispatchers are injected; no `Dispatchers.*` literal, no `GlobalScope`, no `runBlocking` outside tests.
- [ ] No `catch (e: Exception)` around a suspend call that swallows `CancellationException`.
- [ ] Every coroutine outside `viewModelScope`/`rememberCoroutineScope` has a defined cancellation path.

Composables:

- [ ] Composables hold layout and bindings only — no networking, persistence, business rules, or formatting logic.
- [ ] State is hoisted; only the `Screen` composable touches the ViewModel.
- [ ] Every reusable composable takes `modifier: Modifier = Modifier` and applies it to its root.
- [ ] Lazy list items have stable `key`s; no allocation in composition; parameters are immutable or `@Stable`.
- [ ] No side effect in a composable body; `LaunchedEffect`/`DisposableEffect` keys are correct.
- [ ] Bodies over ~60 lines or 2+ nested conditionals are split.
- [ ] Empty, loading and failed states are each rendered explicitly; each has a `@Preview` in light and dark.

External-system boundary:

- [ ] The boundary is reached only through a repository interface; no Retrofit/OkHttp type appears outside `data/`.
- [ ] The repository's public surface is domain types, not DTOs; mappers are explicit and tested.
- [ ] Every external call is behind an interface with a fake, exercised in tests.
- [ ] Failures cross the boundary as a typed result — no raw `IOException`/`HttpException` reaches a ViewModel or composable.
- [ ] Any write that auto-populates a system-of-record value carries a confidence signal and a user-visible confirmation before commit.

Offline (where the feature requires it):

- [ ] Mutations write to a durable Room outbox first; the UI observes Room and does not block on the network.
- [ ] No screen renders a network response directly; Room is the single source of truth.
- [ ] Mutations carry an idempotency key; the outbox drains as unique WorkManager work with a network constraint and backoff.
- [ ] Conflict policy for the entity is stated explicitly, not left to a global default.
- [ ] Any Room schema change ships a tested migration and the exported schema; no `fallbackToDestructiveMigration`.

Background work:

- [ ] The narrowest mechanism is used (WorkManager before a foreground service before an exact alarm); foreground services declare the correct `foregroundServiceType`.
- [ ] No plain service, `Handler` loop or ViewModel coroutine relied on to survive backgrounding.
- [ ] A push is treated as a hint to sync, not as the data; notification channels exist per user-meaningful category.
- [ ] Any request to be exempt from battery optimisation states why the feature is impossible without it.

Capture and on-device ML:

- [ ] Camera/media capture is behind a `core` interface; permission rationales are reviewed as user-facing copy; denied and permanently-denied are separate states.
- [ ] No broad storage permission where the photo picker or scoped storage works; no `Bitmap` passed through navigation or saved state.
- [ ] On-device model inferences are versioned and recorded with their output.
- [ ] A no-model / low-confidence / offline path leaves the user a manual route, not a dead end.

Theming and accessibility:

- [ ] No literal colour, font, `dp`/`sp` spacing or corner radius outside `core:designsystem`.
- [ ] Dark theme and font scale (to 200%) are both implemented for anything this diff touches; insets are handled explicitly.
- [ ] Touch targets meet 48dp; every interactive element has a `contentDescription` or semantics; state is not conveyed by colour alone.

Configuration and secrets:

- [ ] No secret in the repo, `strings.xml`, `BuildConfig` or a committed properties file; credentials are in Keystore-backed storage, never in plain `SharedPreferences`/`DataStore`.
- [ ] No endpoint, threshold, model name, retry count or timeout as a literal at a callsite.
- [ ] New manifest components are `exported="false"` unless justified; no new cleartext or user-CA exception without a stated reason.
- [ ] No PII, identity, token, address, or file path revealing captured user data in logs; no `Log.d`.

Performance:

- [ ] Nothing new blocks the main thread or `Application.onCreate`.
- [ ] No `Context`/`Activity` held in a singleton or static; large images are sampled via the image loader.
- [ ] Any performance claim cites a Macrobenchmark, trace or profiler capture.

Quality:

- [ ] No `!!`, unchecked cast, or `TODO()` on a reachable path; no `lateinit` on a constructor-injectable type.
- [ ] Errors surface through the one typed error hierarchy — no raw `Throwable` reaches a composable.
- [ ] No commented-out code; no `TODO` without a ticket id; new public API has KDoc.

Testing:

- [ ] Every use case, repository and ViewModel touched has unit tests; composables are tested through hoisted `UiState`.
- [ ] A bug fix ships with the test that reproduces it.
- [ ] Repository fakes are the test seam — no test reaches a live external system; no real `delay` or `Thread.sleep`.
- [ ] Migrations and workers touched are covered by migration and worker tests.

## Repo setup — audit once, not per diff

- [ ] Kotlin 2.x with K2, `allWarningsAsErrors` on; no new Java source.
- [ ] Jetpack Compose for product surfaces; View-system interop wrapped in `AndroidView` at the edge only.
- [ ] Gradle Kotlin DSL, version catalog, convention plugins in `build-logic/`; no version literal in a module build file.
- [ ] One Gradle module per feature; explicit API mode on `core:*` and `shared`.
- [ ] Hilt via KSP (not kapt); Room, DataStore and WorkManager in place of `SharedPreferences`/raw SQLite.
- [ ] minSdk is a confirmed, stated decision against the real fleet; targetSdk meets the Play requirement and was moved deliberately.
- [ ] Detekt, ktlint (Spotless) and Android Lint (`warningsAsErrors`) all run in CI; the Lint baseline only shrinks.
- [ ] Release builds are minified and resource-shrunk with scoped keep rules; the release variant is the one tested.
- [ ] `allowBackup` is off or constrained by an explicit allow-list; network security config disables cleartext.
- [ ] A Baseline Profile exists and is generated in CI; StrictMode and LeakCanary are on in debug.
- [ ] Room schemas are exported and committed.
- [ ] Every dependency in the catalog has a stated reason recorded somewhere durable (MR history at minimum).
