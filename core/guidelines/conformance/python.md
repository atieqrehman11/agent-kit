# Python — conformance checklist

The audit list for [`python`](../python.md). Walked by a reviewer, by the delivery gates, and by anyone auditing existing Python.

This is payload, not a guideline: it carries no frontmatter and is never invocable. It lives apart from the rules so that whoever is *writing* code loads the rules without the checklist, and whoever is *auditing* loads the checklist without the rules. Every item below is defined in `python.md` — read it there when a check needs interpreting.

Scope every item to **the diff**, not the repo. A pre-existing violation in a file this change merely touches is a warning naming the file, never a blocker — see the reviewer's severity rules.

---

Complexity — the limits are numbers, so these are pass/fail, not judgement:

- [ ] No function added or changed by this diff exceeds cyclomatic complexity **10** (`C901`).
- [ ] No function exceeds **12** branches (`PLR0912`) or **50** statements (`PLR0915`).
- [ ] Nested blocks reach depth **4** or less (`PLR1702`).
- [ ] No function takes more than **5** parameters (`PLR0913`) or has more than **6** returns (`PLR0911`).
- [ ] `pyproject.toml` selects `C90`, `SIM` and `PL`, and sets the mccabe and pylint limits.
- [ ] Every `# noqa` for a complexity rule carries a comment saying why the function is irreducible.
- [ ] Error conditions use guard clauses and early return rather than a nested `else`.
- [ ] No collapsible `if` nesting that `SIM102` would flag; no `if/elif` chain over a value where a dict or `match` dispatch fits.

Comments — scope to comments this diff adds or edits:

- [ ] No comment restates the line below it, and no docstring only re-spells the signature.
- [ ] No commented-out code, and no `TODO`/`FIXME` without a ticket or an owner.
- [ ] No banner, box-drawing or decoration comments, and no header block repeating the file name or author.
- [ ] Every comment the diff adds says *why* — a constraint, a workaround's reason, or a spec reference.
- [ ] No comment contradicts the code it sits on.

Single responsibility:

- [ ] No function or method name contains `and` or `or`, and none takes a flag parameter that selects between two behaviours.
- [ ] Each class's responsibility states in one sentence with no conjunction.
- [ ] One public concept per module; single-use helpers are private, multi-module helpers live in `src/utils/`.
- [ ] Functions over 50 lines, classes over 200, or modules over 400 were examined for a seam and the size is deliberate.

Tests for new logic:

- [ ] Every conditional, loop and `except` block this diff adds has a test per arm.
- [ ] Every new non-pass-through function or method has a test.
- [ ] Every changed threshold, operator or default has a test on both sides of the boundary.
- [ ] Every bug fix ships a test that fails without the fix.
- [ ] Every domain exception the diff can raise has a test asserting it is raised.
- [ ] Named edge cases are covered: empty input, empty collection, zero results, `None` where the type allows it.
- [ ] Mocks sit at the I/O seam — the repository or client class — not inside the logic under test.
- [ ] Every test asserts a value; none asserts only that the call did not raise.
- [ ] Test names follow `test_given_<state>_when_<action>_then_<outcome>`.

Style and structure:

- [ ] Type hints on every function signature; docstrings on public functions and classes.
- [ ] Line length within 100; `ruff check` and `ruff format` are clean.
- [ ] Imports grouped standard library / third-party / local, separated by blank lines.
- [ ] No duplicated logic that belongs in `src/utils/`.

Error handling and configuration:

- [ ] Exceptions are caught, logged with context, and re-raised — never silently swallowed.
- [ ] In service code, a specific exception is caught and re-raised as a domain exception; a broad `except` appears only in the boundary catch-all.
- [ ] Configuration is loaded and validated, failing loudly on a missing key.
- [ ] No environment-specific value is hardcoded.

Databricks compute (notebook / job / pipeline / agent code only):

- [ ] `print()` driver logging carries context — env, catalog, counts, progress.
- [ ] No `print()` in service code; the `logging` module is used with the level from configuration.
- [ ] DataFrame API preferred over RDDs; PySpark functions preferred over UDFs.
- [ ] Unity Catalog access uses the three-level `catalog.schema.table` namespace.

---
