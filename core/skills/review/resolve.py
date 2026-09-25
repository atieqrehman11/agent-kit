#!/usr/bin/env python3
"""Resolve what a review is about, deterministically, in one run.

    python3 resolve.py [--repo DIR] [--out DIR] [--guidelines DIR] [--comment-lines N] <mr-id | branch>
    python3 resolve.py [--repo DIR] --list

Replaces the fetch / diff / glob-match / grep steps a reviewer used to do one shell call at a
time, and asserts the four ways they fail silently. Writes to --out:

    summary.md          one screen — what the orchestrator reads
    resolve.json        the same, for a script
    meta.json           MR state, branches, title, description, head sha, author
    notes.md            non-system discussion notes, oldest first
    previous_round.md   the last note that is a review (has a VERDICT line) and the replies since
    diff.patch          merge-base..head — this change's own commits only
    files.txt           name-status        numstat.txt
    per_surface/<surface>.patch
    llm_hits.txt        added .py / .sql lines that call a model or a retrieval surface
    tests.patch         the diff restricted to test files
    tests_reaching.txt  for each changed module, the existing tests that import it
    comments.txt        added comment or docstring blocks of --comment-lines or more
    complexity.txt      ruff C90 / PLR over changed .py at the head; limits from the python guideline

Exit codes: 0 ok · 2 usage or not a repo · 3 merged or closed · 4 fetch failed or head == target
· 5 empty diff. The last line on stderr says why.

Read-only: the only git write is `fetch`, which updates refs and never the working tree.
"""

import argparse
import fnmatch
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

# ── resolution of the guidelines directory (STANDARD.md §1.4 order) ──────────────

GUIDELINES_MARKER = "__GUIDELINES_DIR__"


def guidelines_dir(explicit):
    if explicit:
        return explicit
    if not GUIDELINES_MARKER.startswith("__"):
        return GUIDELINES_MARKER
    env = os.environ.get("AGENT_KIT_DATA_DIR")
    if env and os.path.isdir(os.path.join(env, "guidelines")):
        return os.path.join(env, "guidelines")
    d = os.path.dirname(os.path.abspath(__file__))
    while d != os.path.dirname(d):
        if os.path.isfile(os.path.join(d, "STANDARD.md")):
            return os.path.join(d, "core", "guidelines")
        d = os.path.dirname(d)
    die(2, "cannot locate the guidelines directory — pass --guidelines")


# ── the rules resolve.py implements; reference/detection.md is the prose for them ───

# Added lines in .py / .sql that put python-llm in scope.
LLM_TOKENS = [
    "anthropic",
    "openai",
    "bedrock",
    "langchain",
    "langgraph",
    "litellm",
    "mlflow",
    "ChatDatabricks",
    "databricks_langchain",
    "deploy_client",
    "ai_query",
    "ai_extract",
    "ai_classify",
    "ai_parse_document",
    "ai_prep_search",
    "ai_similarity",
    "ai_gen",
    "ai_summarize",
    "ai_translate",
    "ai_analyze_sentiment",
    "ai_mask",
    "ChatCompletion",
    "invoke_model",
    "messages.create",
    "embeddings",
    "vector_search",
    "VectorSearchClient",
    "similarity_search",
    "serving_endpoint",
    "foundation_model",
]

# Surface grouping — first match wins. python/ build and deploy scripts are resolved before
# this table by repo type (see group_files).
SURFACES = [
    (
        "genie",
        [
            r"^src/space\.yml$",
            r"^src/(data_sources|sql_functions|example_queries)\.yml$",
            r"^src/instructions\.md$",
            r"^src/(views|functions)/",
            r"^resources/genie[^/]*\.yml$",
            r"^generated/space\.[^/]*\.json$",
            r"^python/build_space\.py$",
        ],
    ),
    ("agent", [r"^src/managed/", r"^python/(deploy_agent|managed)\.py$"]),
    (
        "frontend",
        [
            r"\.(tsx|jsx|css|scss)$",
            r"(^|/)(package\.json|vite\.config\.[^/]+|tsconfig[^/]*\.json)$",
        ],
    ),
    ("pipeline", [r"(^|/)pipeline/", r"\.pipeline\.yml$"]),
    ("job", [r"\.job\.yml$", r"^src/task_\d\d_[^/]*\.py$", r"^src/ddl/"]),
    (
        "service",
        [
            r"(^|/)(routers|services|repositories|schema)/",
            r"^resources/[^/]*\.app\.yml$",
        ],
    ),
    ("python", [r"\.py$"]),
    ("docs-config", [r".*"]),
]
SURFACE_GUIDELINE = {
    "genie": "genie",
    "agent": "agent",
    "frontend": "react",
    "pipeline": "pipeline",
    "job": "job",
    "service": "service-structure",
}

TEST_PATH = re.compile(
    r"(^|/)tests?/|(^|/)test_[^/]+\.py$|_test\.py$|(^|/)conftest\.py$|\.(test|spec)\.[jt]sx?$"
)
FAN_OUT_LINES = 400  # below this, one reviewer holds every contract
COLLAPSE_BELOW = 3  # a surface with fewer files folds into the largest one

# Complexity limits — mirror `python` guideline §Complexity limits; the sheet is the source.
RUFF_CONFIG = [
    "lint.mccabe.max-complexity=10",
    "lint.pylint.max-branches=12",
    "lint.pylint.max-statements=50",
    "lint.pylint.max-args=5",
    "lint.pylint.max-returns=6",
    "lint.pylint.max-nested-blocks=4",
]
RUFF_SELECT = "C901,PLR0912,PLR0913,PLR0915,PLR0911,PLR1702"

COMMENT_PREFIX = {
    ".py": ("#",),
    ".sql": ("--", "/*", "*"),
    ".yml": ("#",),
    ".yaml": ("#",),
    ".toml": ("#",),
    ".sh": ("#",),
    ".cfg": ("#",),
    ".ini": ("#",),
    ".ts": ("//", "/*", "*"),
    ".tsx": ("//", "/*", "*"),
    ".js": ("//", "/*", "*"),
    ".jsx": ("//", "/*", "*"),
    ".java": ("//", "/*", "*"),
    ".css": ("/*", "*"),
}

# ── helpers ────────────────────────────────────────────────────────────────────────


def die(code, msg):
    print(msg, file=sys.stderr)
    sys.exit(code)


def run(cmd, cwd, check=True, text=True):
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=text)
    if check and p.returncode != 0:
        raise subprocess.CalledProcessError(p.returncode, cmd, p.stdout, p.stderr)
    return p.stdout


def git(repo, *args, check=True):
    return run(["git", *args], repo, check=check)


def glab_json(repo, *args):
    try:
        return json.loads(run(["glab", *args], repo))
    except (FileNotFoundError, subprocess.CalledProcessError, json.JSONDecodeError):
        return None


def write(out, name, text):
    p = os.path.join(out, name)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        f.write(text if text.endswith("\n") or not text else text + "\n")
    return name


def frontmatter_globs(gdir):
    """name -> applies_to globs, read from each guideline's frontmatter. The globs are the mapping."""
    out = {}
    for f in sorted(os.listdir(gdir)):
        if not f.endswith(".md"):
            continue
        text = open(os.path.join(gdir, f), encoding="utf-8").read()
        m = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
        if not m:
            continue
        fm = m.group(1)
        am = re.search(r"^applies_to:\s*\n((?:\s+-\s+.*\n?)+)", fm, re.MULTILINE)
        globs = (
            re.findall(r"-\s+[\"']?([^\"'\n]+?)[\"']?\s*$", am.group(1), re.MULTILINE)
            if am
            else []
        )
        out[f[:-3]] = globs
    return out


def glob_match(path, g):
    if fnmatch.fnmatch(path, g):
        return True
    return g.startswith("**/") and fnmatch.fnmatch(path, g[3:])


# ── step 1: what is being reviewed ────────────────────────────────────────────────


def list_open(repo):
    mrs = glab_json(repo, "mr", "list", "-F", "json", "--per-page", "50")
    if mrs is None:
        die(
            2, "glab is not available or not authenticated — cannot list merge requests"
        )
    if not mrs:
        print("no open merge requests")
        return
    for m in mrs:
        d = " (draft)" if m.get("draft") else ""
        print(
            f"!{m['iid']:<5} {m['source_branch']} → {m['target_branch']}  {m['title']}{d}  · {m['author']['username']}"
        )


def default_branch(repo):
    out = git(repo, "ls-remote", "--symref", "origin", "HEAD")
    m = re.search(r"ref: refs/heads/(\S+)\s+HEAD", out)
    return m.group(1) if m else "main"


def resolve_target(repo, arg):
    """Returns meta dict. api=False means state is unknowable and the target is assumed."""
    iid = None
    if re.fullmatch(r"!?\d+", arg):
        iid = int(arg.lstrip("!"))
    else:
        mrs = glab_json(repo, "mr", "list", "-F", "json", "--source-branch", arg)
        if mrs:
            iid = mrs[0]["iid"]
    meta = {"iid": iid, "api": False, "assumed": True, "branch": None if iid else arg}
    if iid is not None:
        d = glab_json(repo, "api", f"projects/:id/merge_requests/{iid}")
        if d:
            meta.update(
                api=True,
                assumed=False,
                state=d["state"],
                draft=bool(d.get("draft")),
                source_branch=d["source_branch"],
                target_branch=d["target_branch"],
                title=d["title"],
                description=d.get("description") or "",
                api_sha=d.get("sha"),
                web_url=d.get("web_url"),
                author=(d.get("author") or {}).get("username"),
            )
    if not meta["api"]:
        meta.update(
            state="unknown",
            draft=False,
            target_branch=default_branch(repo),
            title="",
            description="",
            source_branch=arg if iid is None else None,
            api_sha=None,
            web_url=None,
            author=None,
        )
    return meta


def read_notes(repo, meta):
    if not meta["api"]:
        return []
    notes, page = [], 1
    while True:
        batch = glab_json(
            repo,
            "api",
            f"projects/:id/merge_requests/{meta['iid']}/notes?per_page=100&sort=asc&page={page}",
        )
        if not batch:
            break
        notes += [n for n in batch if not n.get("system")]
        if len(batch) < 100:
            break
        page += 1
    return notes


VERDICT_LINE = re.compile(r"^\W*VERDICT\b", re.MULTILINE)


def rounds(notes):
    reviews = [
        i for i, n in enumerate(notes) if VERDICT_LINE.search(n.get("body") or "")
    ]
    if not reviews:
        return 1, None, []
    last = reviews[-1]
    return len(reviews) + 1, notes[last], notes[last + 1 :]


def fmt_note(n):
    return f"### {(n.get('author') or {}).get('username', '?')} · {n.get('created_at', '')[:10]}\n\n{n.get('body', '')}\n"


def fetch_and_diff(repo, meta, out):
    target = meta["target_branch"]
    try:
        git(repo, "fetch", "-q", "origin", target)
        if meta["iid"] is not None:
            git(
                repo, "fetch", "-q", "origin", f"refs/merge-requests/{meta['iid']}/head"
            )
        else:
            git(repo, "fetch", "-q", "origin", meta["branch"])
    except subprocess.CalledProcessError as e:
        die(4, f"fetch failed: {e.stderr.strip().splitlines()[-1] if e.stderr else e}")
    head = git(repo, "rev-parse", "FETCH_HEAD").strip()
    base_tip = git(repo, "rev-parse", f"origin/{target}").strip()
    if head == base_tip:
        die(
            4,
            f"FETCH_HEAD equals origin/{target} — the merge request head was not fetched; nothing was diffed",
        )
    if meta.get("api_sha") and meta["api_sha"] != head:
        meta["sha_note"] = (
            f"API head {meta['api_sha'][:9]} differs from fetched {head[:9]} — a push landed between the two reads"
        )
    merge_base = git(repo, "merge-base", base_tip, head).strip()
    patch = git(repo, "diff", merge_base, head)
    if not patch.strip():
        die(
            5,
            f"empty diff: origin/{target}...{head[:9]} — nothing to review (never fall back to a two-dot diff)",
        )
    write(out, "diff.patch", patch)
    write(out, "files.txt", git(repo, "diff", "--name-status", merge_base, head))
    numstat = git(repo, "diff", "--numstat", merge_base, head)
    write(out, "numstat.txt", numstat)
    added = deleted = 0
    for line in numstat.splitlines():
        a, d, _ = line.split("\t", 2)
        if a.isdigit():
            added += int(a)
            deleted += int(d)
    status = {}
    for line in git(repo, "diff", "--name-status", merge_base, head).splitlines():
        parts = line.split("\t")
        status[parts[-1]] = parts[0][0]
    return head, base_tip, merge_base, patch, status, added, deleted


# ── step 2: surfaces and guidelines ───────────────────────────────────────────────


def added_lines(patch):
    """{path: [(new_lineno, text), ...]} for every added line."""
    out, path, lineno = {}, None, 0
    for line in patch.splitlines():
        if line.startswith("+++ "):
            path = line[6:] if line.startswith("+++ b/") else None
            continue
        if line.startswith("@@"):
            m = re.match(r"@@ -\d+(?:,\d+)? \+(\d+)", line)
            lineno = int(m.group(1)) if m else 0
            continue
        if path is None or line.startswith("---"):
            continue
        if line.startswith("+"):
            out.setdefault(path, []).append((lineno, line[1:]))
            lineno += 1
        elif not line.startswith("-") and not line.startswith("\\"):
            lineno += 1
    return out


def repo_type(repo, head):
    tree = git(repo, "ls-tree", "-r", "--name-only", head).splitlines()
    if any(p.startswith("src/managed/") for p in tree):
        return "agent"
    if "src/space.yml" in tree:
        return "genie"
    return None


def surface_of(path, rtype, repo, head):
    if (
        path.startswith("python/")
        and path.endswith(".py")
        and rtype in ("agent", "genie")
    ):
        return rtype
    if rtype == "agent" and re.match(r"^resources/[^/]*\.job\.yml$", path):
        body = git(repo, "show", f"{head}:{path}", check=False)
        if "managed" in body or "deploy_agent" in body:
            return "agent"
    for name, pats in SURFACES:
        if any(re.search(p, path) for p in pats):
            return name
    return "docs-config"


CODE_SURFACES = ("service", "job", "pipeline", "agent", "genie", "frontend")


def group_files(files, rtype, repo, head, changed_lines):
    """Tests are given to every reviewer rather than grouped; Other Python folds into the
    largest code surface; any surface under COLLAPSE_BELOW files folds into the largest."""
    groups = {}
    for f in files:
        if TEST_PATH.search(f):
            continue
        groups.setdefault(surface_of(f, rtype, repo, head), []).append(f)
    collapsed = []
    code = [k for k in groups if k in CODE_SURFACES]
    if "python" in groups and code:
        target = max(code, key=lambda k: len(groups[k]))
        groups[target] += groups.pop("python")
        collapsed.append("python")
    if len(groups) > 1:
        largest = max(groups, key=lambda k: len(groups[k]))
        for k in [
            k for k in groups if k != largest and len(groups[k]) < COLLAPSE_BELOW
        ]:
            groups[largest] += groups.pop(k)
            collapsed.append(k)
    fan_out = changed_lines > FAN_OUT_LINES and len(groups) > 1
    return groups, collapsed, fan_out


def guidelines_for(files, globs, added, rtype):
    """(matched-by-glob, added-by-detection) guideline names, plus the LLM hit lines."""
    by_glob, by_det, hits = set(), {}, []
    for f in files:
        for name, gs in globs.items():
            if any(glob_match(f, g) for g in gs):
                by_glob.add(name)
    exts = {os.path.splitext(f)[1] for f in files}
    if ".py" in exts and "python" in globs:
        by_glob.add("python")
    if ".java" in exts and "java" in globs:
        by_glob.add("java")
    for f, lines in added.items():
        if os.path.splitext(f)[1] not in (".py", ".sql"):
            continue
        for n, t in lines:
            if any(tok in t for tok in LLM_TOKENS):
                hits.append(f"{f}:{n}  {t.strip()[:120]}")
    if hits and "python-llm" in globs:
        by_det["python-llm"] = f"{len(hits)} model or retrieval calls in added lines"
    if (
        any(f == "python/validate.py" or f.startswith("python/") for f in files)
        and rtype
    ):
        if rtype not in by_glob:
            by_det[rtype] = (
                f"python/ scripts in a repo holding {'src/managed/' if rtype == 'agent' else 'src/space.yml'}"
            )
    return sorted(by_glob), by_det, hits


# ── step 3: the mechanical checks a reviewer forgets ─────────────────────────────


def tests_section(repo, merge_base, head, files, out):
    test_files = [f for f in files if TEST_PATH.search(f)]
    patch = git(repo, "diff", merge_base, head, "--", *test_files) if test_files else ""
    write(out, "tests.patch", patch)
    modules = [
        f
        for f in files
        if f.endswith(".py")
        and not TEST_PATH.search(f)
        and not f.endswith("__init__.py")
    ]
    reaching, lines = {}, []
    for m in modules:
        stem = os.path.splitext(os.path.basename(m))[0]
        hits = git(
            repo,
            "grep",
            "-l",
            "-w",
            "-e",
            stem,
            "--and",
            "-e",
            "import",
            head,
            "--",
            ":(glob)**/test_*.py",
            ":(glob)**/*_test.py",
            ":(glob)**/tests/**",
            ":(glob)**/conftest.py",
            ":(glob)**/*.test.*",
            ":(glob)**/*.spec.*",
            check=False,
        )
        tests = sorted({h.split(":", 1)[1] for h in hits.splitlines() if ":" in h})
        reaching[m] = tests
        lines.append(
            f"{m}\n    "
            + (
                "\n    ".join(tests)
                if tests
                else "— no existing test imports this module"
            )
        )
    write(
        out,
        "tests_reaching.txt",
        "\n".join(lines) or "no changed Python modules outside tests",
    )
    return test_files, reaching


def py_comment_lines(source):
    """(comment line numbers, docstring line numbers) from the tokenizer and the AST, so a
    triple-quote opened outside the diff cannot leak state into it. None on a syntax error."""
    import ast
    import io
    import tokenize

    comments, docs = set(), set()
    try:
        for tok in tokenize.generate_tokens(io.StringIO(source).readline):
            if tok.type == tokenize.COMMENT:
                comments.add(tok.start[0])
        tree = ast.parse(source)
    except (SyntaxError, tokenize.TokenError):
        return None
    for node in ast.walk(tree):
        body = getattr(node, "body", None)
        if isinstance(body, list) and body and isinstance(body[0], ast.Expr):
            v = body[0].value
            if isinstance(v, ast.Constant) and isinstance(v.value, str):
                docs.update(range(body[0].lineno, body[0].end_lineno + 1))
    return comments, docs


def comment_blocks(added, min_lines, source_of):
    blocks = []
    for path, lines in added.items():
        ext = os.path.splitext(path)[1]
        prefixes = COMMENT_PREFIX.get(ext)
        if ext == ".md" or not prefixes:
            continue
        py = py_comment_lines(source_of(path)) if ext == ".py" else None
        cur, prev_n = [], None
        for n, t in lines:
            s = t.strip()
            if py is not None:
                kind = (
                    "docstring"
                    if n in py[1]
                    else "comment"
                    if n in py[0] and s.startswith("#")
                    else None
                )
            else:
                kind = "comment" if s.startswith(prefixes) else None
            if (
                kind
                and prev_n is not None
                and n == prev_n + 1
                and cur
                and cur[-1][2] == kind
            ):
                cur.append((n, s, kind))
            else:
                if len(cur) >= min_lines:
                    blocks.append((path, cur))
                cur = [(n, s, kind)] if kind else []
            prev_n = n
        if len(cur) >= min_lines:
            blocks.append((path, cur))
    seen, rows, kinds = {}, [], {"comment": 0, "docstring": 0}
    for path, blk in blocks:
        key = re.sub(r"\W+", " ", " ".join(s for _, s, _ in blk)).lower()[:200]
        loc = f"{path}:{blk[0][0]}"
        rep = f"  (near-identical to {seen[key]})" if key in seen else ""
        seen.setdefault(key, loc)
        kind = blk[0][2]
        kinds[kind] += 1
        preview = next((s for _, s, _ in blk if re.search(r"[A-Za-z]{3}", s)), blk[0][1])
        preview = preview.strip("#/-*'\" ")[:70]
        rows.append(f'{loc}  {len(blk)} lines  {kind:<9} "{preview}"{rep}')
    return rows, kinds


def complexity(repo, head, files, status, added, out):
    pys = [f for f in files if f.endswith(".py") and status.get(f) != "D"]
    if not pys:
        write(out, "complexity.txt", "no Python files changed")
        return [], 0, 0
    if not shutil.which("ruff"):
        write(
            out,
            "complexity.txt",
            "ruff not installed — the Complexity row must be assessed by hand",
        )
        return ["ruff not installed"], 0, 0
    tmp = tempfile.mkdtemp(prefix="review-cx-")
    try:
        for f in pys:
            dst = os.path.join(tmp, f)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            with open(dst, "w", encoding="utf-8") as fh:
                fh.write(git(repo, "show", f"{head}:{f}"))
        cmd = [
            "ruff",
            "check",
            "--isolated",
            "--no-cache",
            "--preview",
            "--output-format",
            "concise",
            "--select",
            RUFF_SELECT,
            "--exit-zero",
        ]
        for c in RUFF_CONFIG:
            cmd += ["--config", c]
        raw = run(cmd + pys, tmp, check=False)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    rows, n_added, n_touched = [], 0, 0
    for line in raw.splitlines():
        m = re.match(r"^(.*?):(\d+):\d+: (\w+) (.*)$", line)
        if not m:
            continue
        path, ln, code, msg = m.group(1), int(m.group(2)), m.group(3), m.group(4)
        in_diff = any(n == ln for n, _ in added.get(path, []))
        n_added += in_diff
        n_touched += not in_diff
        rows.append(
            f"{path}:{ln}  {code}  {msg}  [{'added by this diff' if in_diff else 'pre-existing, touched'}]"
        )
    write(
        out,
        "complexity.txt",
        "\n".join(rows) or "ruff: no complexity findings in changed files",
    )
    return rows, n_added, n_touched


# ── main ───────────────────────────────────────────────────────────────────────────


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument(
        "target", nargs="?", help="MR id (142 or !142) or a source branch name"
    )
    ap.add_argument("--repo", default=os.getcwd())
    ap.add_argument(
        "--out", help="output directory (default: a temp dir named for the repo and MR)"
    )
    ap.add_argument(
        "--guidelines",
        help="guidelines directory; resolved per STANDARD.md when omitted",
    )
    ap.add_argument(
        "--comment-lines",
        type=int,
        default=5,
        help="report added comment blocks of at least N lines",
    )
    ap.add_argument(
        "--list", action="store_true", help="list open merge requests and exit"
    )
    a = ap.parse_args()

    repo = os.path.abspath(a.repo)
    if git(repo, "rev-parse", "--is-inside-work-tree", check=False).strip() != "true":
        die(2, f"{repo} is not a git repository")
    if a.list:
        return list_open(repo)
    if not a.target:
        die(2, "give an MR id or a branch name, or --list")

    gdir = guidelines_dir(a.guidelines)
    meta = resolve_target(repo, a.target)
    if meta["api"] and meta["state"] != "opened":
        die(3, f"!{meta['iid']} is {meta['state']} — nothing to review")
    label = f"!{meta['iid']}" if meta["iid"] is not None else meta["branch"]
    out = a.out or os.path.join(
        tempfile.gettempdir(), f"review-{os.path.basename(repo)}-{label.strip('!')}"
    )
    os.makedirs(out, exist_ok=True)

    notes = read_notes(repo, meta)
    round_no, prev, replies = rounds(notes)
    write(
        out, "notes.md", "\n".join(fmt_note(n) for n in notes) or "no discussion notes"
    )
    if prev:
        write(
            out,
            "previous_round.md",
            "# Previous review\n\n"
            + fmt_note(prev)
            + "\n# Replies since\n\n"
            + ("\n".join(fmt_note(n) for n in replies) or "none"),
        )

    head, base_tip, merge_base, patch, status, n_add, n_del = fetch_and_diff(
        repo, meta, out
    )
    files = list(status)
    added = added_lines(patch)
    changed = n_add + n_del
    rtype = repo_type(repo, head)
    globs = frontmatter_globs(gdir)

    groups, collapsed, fan_out = group_files(files, rtype, repo, head, changed)
    surfaces = {}
    for name, fs in groups.items():
        by_glob, by_det, _ = guidelines_for(
            fs, globs, {f: added.get(f, []) for f in fs}, rtype
        )
        g = SURFACE_GUIDELINE.get(name)
        if name == "docs-config":
            g = rtype or ("api" if "service" in groups else None)
        if g and g in globs and g not in by_glob:
            by_det[g] = (
                "repo-type guideline" if name == "docs-config" else "surface guideline"
            )
        surfaces[name] = {
            "files": sorted(fs),
            "guidelines": by_glob,
            "detected": by_det,
            "patch": write(
                out,
                f"per_surface/{name}.patch",
                git(repo, "diff", merge_base, head, "--", *fs),
            ),
        }
    all_glob, all_det, hits = guidelines_for(files, globs, added, rtype)
    write(
        out,
        "llm_hits.txt",
        "\n".join(hits) or "no model or retrieval calls in added .py/.sql lines",
    )

    test_files, reaching = tests_section(repo, merge_base, head, files, out)
    untested = [m for m, t in reaching.items() if not t]
    cblocks, ckinds = comment_blocks(added, a.comment_lines, lambda f: git(repo, "show", f"{head}:{f}", check=False))
    tests_in_diff = [f for f in files if TEST_PATH.search(f)]
    binaries = sorted(
        {
            m.group(1)
            for m in re.finditer(r"^Binary files (?:a/)?(\S+) and", patch, re.M) if m.group(1) != "/dev/null"
        }
        | {
            f
            for f in files
            if f.endswith((".whl", ".png", ".jpg", ".pdf", ".zip", ".jar", ".parquet"))
        }
    )
    write(
        out,
        "comments.txt",
        "\n".join(cblocks) or f"no added comment blocks of {a.comment_lines}+ lines",
    )
    cx_rows, cx_added, cx_touched = complexity(repo, head, files, status, added, out)

    write(
        out,
        "meta.json",
        json.dumps(
            {
                **meta,
                "head": head,
                "base_tip": base_tip,
                "merge_base": merge_base,
                "round": round_no,
            },
            indent=2,
        ),
    )

    def fmt_g(s):
        return (
            ", ".join(
                s["guidelines"]
                + [f"{k} (detected: {v})" for k, v in s["detected"].items()]
            )
            or "none"
        )

    mr_line = (
        f"{label} {meta['state']} · {meta.get('source_branch') or '?'} → {meta['target_branch']}"
        f'{" (assumed)" if meta["assumed"] else ""} · "{meta["title"]}" · by {meta["author"] or "?"}'
        f" · head {head[:9]} · draft: {'yes' if meta['draft'] else 'no'}"
        + (
            ""
            if meta["iid"] is not None
            else " · NO MERGE REQUEST — branch diffed against the default branch"
        )
    )
    round_line = f"{round_no}" + (
        f" · previous review by {(prev.get('author') or {}).get('username', '?')} on "
        f"{prev.get('created_at', '')[:10]} → previous_round.md · {len(replies)} replies since"
        if prev
        else " · first review"
    )
    lines = [
        f"# Review resolve — {os.path.basename(repo)} {label}",
        "",
        f"MR         {mr_line}",
        f"Round      {round_line}",
        f"Diff       {len(files)} files · +{n_add} / −{n_del} · {changed} changed lines · base {merge_base[:9]}",
        f"Fan-out    {'yes — ' + str(len(groups)) + ' surfaces over ' + str(FAN_OUT_LINES) + ' lines: one reviewer per surface' if fan_out else 'no — one reviewer holds every contract below'}",
        "Surfaces"
        + (
            f"   (folded into the largest: {', '.join(collapsed)})" if collapsed else ""
        ),
    ]
    for name, s in surfaces.items():
        lines.append(f"  {name} ({len(s['files'])} files): {fmt_g(s)}  → {s['patch']}")
    if tests_in_diff:
        lines.append(
            f"  tests ({len(tests_in_diff)} files): given to every reviewer as tests.patch, not a surface"
        )
    lines += [
        f"Detected   {', '.join(f'{k}: {v}' for k, v in all_det.items()) or 'nothing beyond the globs'}"
        + (" → llm_hits.txt" if hits else ""),
        f"Tests      {len(test_files)} test files in the diff → tests.patch · "
        f"{len(untested)} of {len(reaching)} changed modules have no existing test importing them → tests_reaching.txt",
        f"Comments   {len(cblocks)} added blocks of {a.comment_lines}+ lines "
        f"({ckinds['comment']} comments, {ckinds['docstring']} docstrings) → comments.txt",
        f"Complexity {cx_added} findings on added lines, {cx_touched} pre-existing in touched files → complexity.txt"
        if cx_rows != ["ruff not installed"]
        else "Complexity ruff not installed — assess by hand",
        f"Repo type  {rtype or 'service / generic'}",
    ]
    if binaries:
        lines.append(
            f"Binary     {len(binaries)} binary files in the diff, not reviewable as text: {', '.join(binaries[:6])}"
            + (" …" if len(binaries) > 6 else "")
        )
    if meta.get("sha_note"):
        lines.append(f"Warning    {meta['sha_note']}")
    if meta.get("description"):
        lines += ["", "## MR description", "", meta["description"]]
    write(out, "summary.md", "\n".join(lines))
    write(
        out,
        "resolve.json",
        json.dumps(
            {
                "meta": meta,
                "head": head,
                "merge_base": merge_base,
                "round": round_no,
                "files": status,
                "added": n_add,
                "deleted": n_del,
                "changed": changed,
                "fan_out": fan_out,
                "collapsed": collapsed,
                "surfaces": surfaces,
                "detected": all_det,
                "llm_hits": len(hits),
                "test_files": test_files,
                "modules_without_tests": untested,
                "comment_blocks": len(cblocks),
                "complexity": {"added": cx_added, "touched": cx_touched},
                "repo_type": rtype,
                "out": out,
            },
            indent=2,
        ),
    )
    print(f"{out}/summary.md")


if __name__ == "__main__":
    main()
