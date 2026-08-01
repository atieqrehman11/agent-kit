#!/usr/bin/env python3
"""Scaffold an eval spec inside the repo that will OWN it.

Writes ``<repo>/evaluation/`` = spec.py + run.sh + README.md + starter questions.csv +
benchmark.csv, wired to the target the caller chose. Each use case owns its own eval
spec and data; the shared eval engine is generic and is *imported* (as the installed
``harness`` package), never copied into a repo.

Usage:
    python3 new.py --slug <kebab> --target <target> --repo <path> \\
        [--display-name "<name>"] [--endpoint <name-or-url>] \\
        [--engine-path <path>] [--force]

Targets:
    agent-responses   deployed agent serving endpoint, 'responses' schema (MAS/ChatAgent)
    agent-chat        deployed agent serving endpoint, chat/ChatCompletion schema
    http-backend      REST backend answering {"query": ...} -> {"answer": ...}
    openai            OpenAI-compatible chat endpoint

Token resolution (first match wins), mirroring /scaffold:new:
    endpoint       --endpoint  >  transport default (local URL, or a TODO_SET_ token)
    engine path    --engine-path  >  $EVAL_ENGINE_PATH  >  profile `eval_engine_path`
                   >  TODO_SET_EVAL_ENGINE_PATH (the generated run.sh then auto-detects a
                   sibling checkout, or takes EVAL_ENGINE_PATH at run time)

Output: <repo>/evaluation/
"""

import argparse
import json
import os
import shutil
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATES = os.path.join(_HERE, "templates")

ENGINE_TODO = "TODO_SET_EVAL_ENGINE_PATH"
ENDPOINT_TODO = "TODO_SET_AGENT_ENDPOINT"

# target -> (human label, transport, request adapter, response adapter). The adapter keys
# are the engine's own contract names (harness/agent/adapters.py), not project-specific.
TARGETS = {
    "agent-responses": (
        "Deployed agent (serving endpoint, 'responses' schema)",
        "databricks",
        "databricks_responses",
        "databricks_responses",
    ),
    "agent-chat": (
        "Deployed agent (serving endpoint, chat schema)",
        "databricks",
        "databricks_chat",
        "databricks_chat",
    ),
    "http-backend": (
        'REST backend over HTTP (POST {"query": ...} -> {"answer": ...})',
        "http",
        "http_query",
        "http_answer",
    ),
    "openai": (
        "OpenAI-compatible chat endpoint over HTTP",
        "http",
        "openai_chat",
        "openai_chat",
    ),
}

# Per-transport endpoint default when the caller supplies none: a serving-endpoint name
# can't be guessed (leave a placeholder), a local HTTP URL is a runnable starting point.
_DEFAULT_ENDPOINT = {
    "databricks": ENDPOINT_TODO,
    "http": "http://localhost:8000/v1/chat/query",
}


# Shared install profile saved by /scaffold:profile, in the .claude/ root (two levels up
# from this skill dir). Returns only non-empty string values; {} when there is no profile.
def _load_profile():
    root = os.path.dirname(os.path.dirname(_HERE))
    path = os.path.join(root, "scaffold-profile.json")
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return {k: v for k, v in data.items() if isinstance(v, str) and v.strip()}
    except (FileNotFoundError, ValueError):
        return {}


def _resolve_engine_path(cli_value, profile):
    """--engine-path > $EVAL_ENGINE_PATH > profile > TODO placeholder (no hardcoded path)."""
    chosen = (
        cli_value
        or os.environ.get("EVAL_ENGINE_PATH")
        or profile.get("eval_engine_path")
    )
    if not chosen:
        return ENGINE_TODO
    return os.path.expanduser(os.path.expandvars(chosen))


def parse_args(argv):
    p = argparse.ArgumentParser(description="Scaffold an eval spec in a use-case repo.")
    p.add_argument("--slug", required=True, help="kebab-case use-case identifier")
    p.add_argument(
        "--target",
        required=True,
        choices=sorted(TARGETS),
        help="what the spec evaluates",
    )
    p.add_argument("--repo", required=True, help="repo that will own the eval")
    p.add_argument("--display-name", default="", help="default: Title Case of the slug")
    p.add_argument(
        "--endpoint", default="", help="serving-endpoint name, or an http(s):// URL"
    )
    p.add_argument(
        "--engine-path",
        default="",
        help="eval engine checkout (default: profile/env/TODO)",
    )
    p.add_argument(
        "--force", action="store_true", help="overwrite an existing evaluation/spec.py"
    )
    return p.parse_args(argv)


def main(argv=None):
    args = parse_args(argv if argv is not None else sys.argv[1:])
    profile = _load_profile()

    slug = args.slug.strip()
    display_name = args.display_name.strip() or slug.replace("-", " ").title()
    repo_root = os.path.abspath(
        os.path.expanduser(os.path.expandvars(args.repo.strip()))
    )

    if not os.path.isdir(repo_root):
        sys.exit(
            f"ERROR: repo not found at {repo_root}\n"
            f"       Pass the path to the repo that will OWN this eval."
        )

    label, transport, request, adapter = TARGETS[args.target]
    endpoint = args.endpoint.strip() or _DEFAULT_ENDPOINT[transport]
    engine_path = _resolve_engine_path(args.engine_path.strip(), profile)

    if transport == "databricks":
        endpoint_hint = "a serving-endpoint name"
        token_note = ""
    else:
        endpoint_hint = "an http(s):// URL"
        token_note = "If the backend needs a bearer token, set `AGENT_AUTH_TOKEN=...`."

    resource_key = slug.replace("-", "_")  # spec `name`

    # If the caller pointed at the evaluation/ folder itself, don't nest another.
    dest = (
        repo_root
        if os.path.basename(repo_root) == "evaluation"
        else os.path.join(repo_root, "evaluation")
    )
    spec_path = os.path.join(dest, "spec.py")
    if os.path.exists(spec_path) and not args.force:
        sys.exit(
            f"ERROR: a spec already exists at {spec_path}\n"
            f"       Edit it directly, or re-run with --force to regenerate."
        )

    print("=" * 62)
    print(f"  Scaffolding eval spec: {resource_key}")
    print(f"  Target:  {label}")
    print(f"  Into:    {dest}")
    print("=" * 62)

    os.makedirs(dest, exist_ok=True)

    vars_ = {
        "TPLVAR_SPEC": resource_key,
        "TPLVAR_USE_CASE": slug,
        "TPLVAR_DISPLAY_NAME": display_name,
        "TPLVAR_TARGET_LABEL": label,
        "TPLVAR_TRANSPORT": transport,
        "TPLVAR_REQUEST": request,
        "TPLVAR_ADAPTER": adapter,
        "TPLVAR_ENDPOINT_HINT": endpoint_hint,
        "TPLVAR_ENDPOINT": endpoint,
        "TPLVAR_ENGINE_PATH": engine_path,
        "TPLVAR_TOKEN_NOTE": token_note,
    }

    for src, out, mode in (
        ("spec.py.tmpl", "spec.py", 0o644),
        ("README.md.tmpl", "README.md", 0o644),
        ("run.sh.tmpl", "run.sh", 0o755),
    ):
        path = _render(os.path.join(TEMPLATES, src), os.path.join(dest, out), vars_)
        os.chmod(path, mode)
        print(f"  [spec] created {out}")

    # Results are regenerable run artifacts — keep them out of git.
    with open(os.path.join(dest, ".gitignore"), "w", encoding="utf-8") as f:
        f.write("# eval run artifacts (report + tables) — regenerable\neval-results/\n")
    print("  [spec] created .gitignore")

    for csv_name in ("questions.csv", "benchmark.csv"):
        shutil.copy(os.path.join(TEMPLATES, csv_name), os.path.join(dest, csv_name))
        print(f"  [spec] created {csv_name}")

    _next_steps(dest, endpoint, transport, engine_path)
    return 0


def _render(src, dst, replacements):
    with open(src, encoding="utf-8") as f:
        content = f.read()
    # Longest token first so a token that is a prefix of another (TPLVAR_ENDPOINT vs
    # TPLVAR_ENDPOINT_HINT) doesn't corrupt the longer one.
    for k in sorted(replacements, key=len, reverse=True):
        content = content.replace(k, replacements[k])
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    with open(dst, "w", encoding="utf-8") as f:
        f.write(content)
    return dst


def _next_steps(dest, endpoint, transport, engine_path):
    print(f"\n  Scaffolded: {dest}\n")
    print("  Next steps (run from the repo that owns the eval):")
    print("    1. Edit evaluation/questions.csv             — the smoke question set")
    print("    2. Fill evaluation/benchmark.csv             — the hard set")
    print("       (set human_approval_status='approved' on rows to include them)")
    if endpoint.startswith("TODO_SET_"):
        print("    3. Set default_endpoint in evaluation/spec.py")
        print(
            "       or pass it at runtime:  AGENT_ENDPOINT=... ./evaluation/run.sh smoke"
        )
    else:
        print(
            f"    3. Confirm default_endpoint in evaluation/spec.py  (currently {endpoint})"
        )
    if transport == "http":
        print("       (if the backend needs a token:  AGENT_AUTH_TOKEN=... )")
    print("    4. Run:  ./evaluation/run.sh smoke     (installs the engine if needed)")
    print(
        "       then: ./evaluation/run.sh hard      (once benchmark rows are approved)"
    )
    print("    ·  Inspect the spec first:  ./evaluation/run.sh --show")
    if engine_path == ENGINE_TODO:
        print(
            "    ·  Engine path unset — run.sh auto-detects a sibling checkout providing"
        )
        print(
            "       `harness`; otherwise set EVAL_ENGINE_PATH=... (or fill eval_engine_path"
        )
        print("       in the shared profile and re-run /scaffold:profile).")
    else:
        print(f"    ·  Engine: {engine_path}  (override with EVAL_ENGINE_PATH=...)")
    print()


if __name__ == "__main__":
    raise SystemExit(main())
