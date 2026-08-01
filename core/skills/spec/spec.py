#!/usr/bin/env python3
"""Feature spec lifecycle: create a spec, and check it for completeness.

Two subcommands:

  new    allocate the next feature number, create <specs-root>/<NNN>-<slug>/
         with spec.md + tasks.md rendered from templates.

  check  parse spec.md + tasks.md and validate them. Deterministic gates only —
         anything requiring judgement belongs in the command markdown, not here.

Specs root resolution (first hit wins):
  --specs-root  >  $SPEC_ROOT  >  ~/.claude/spec-profile.json "specs_root"  >  ./specs

Columns are always looked up by header name. Users reorder columns for readability and
position-based access silently reads the wrong one and returns plausible garbage.
"""

import argparse
import datetime
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATES = os.path.join(HERE, "templates")
PROFILE = os.path.join(os.path.expanduser("~"), ".claude", "spec-profile.json")

PRIORITIES = {"P0", "P1", "P2", "P3"}
STATUSES = {"TODO", "WIP", "DONE", "BLOCKED"}
MAX_DAYS = 5.0

REQ_ID = re.compile(r"^(FR|NFR)-\d+[a-z]?$")
DEC_ID = re.compile(r"^D-\d+[a-z]?$")


# ---------------------------------------------------------------- resolution


def load_profile():
    try:
        with open(PROFILE) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def resolve_specs_root(cli_value):
    root = (
        cli_value
        or os.environ.get("SPEC_ROOT")
        or load_profile().get("specs_root")
        or os.path.join(os.getcwd(), "specs")
    )
    return os.path.abspath(os.path.expanduser(root))


def next_number(specs_root):
    """Next sequential feature number, zero-padded to 3."""
    highest = 0
    if os.path.isdir(specs_root):
        for name in os.listdir(specs_root):
            m = re.match(r"^(\d+)-", name)
            if m:
                highest = max(highest, int(m.group(1)))
    return f"{highest + 1:03d}"


# ------------------------------------------------------------ table parsing


def parse_tables(text):
    """Every markdown pipe table in `text`, as a list of dicts keyed by header.

    Returns [{"headers": [...], "rows": [{header: cell}], "line": n}].
    A row whose cell count differs from the header count is kept and padded, so a
    malformed row surfaces as a validation error rather than vanishing.
    """
    tables = []
    current = None
    for lineno, line in enumerate(text.splitlines(), 1):
        stripped = line.strip()
        is_row = (
            stripped.startswith("|") and stripped.endswith("|") and len(stripped) > 1
        )
        if not is_row:
            current = None
            continue
        cells = [c.strip() for c in stripped[1:-1].split("|")]
        if current is None:
            current = {"headers": cells, "rows": [], "line": lineno}
            tables.append(current)
            continue
        if all(set(c) <= set("-: ") and c for c in cells):
            continue  # separator row
        while len(cells) < len(current["headers"]):
            cells.append("")
        row = dict(zip(current["headers"], cells))
        row["_line"] = lineno
        current["rows"].append(row)
    return tables


def find_table(tables, *required_headers):
    """First table containing every required header. None if absent."""
    for t in tables:
        if all(h in t["headers"] for h in required_headers):
            return t
    return None


def split_ids(cell):
    """Comma/space separated ID list. '-' and '' mean none."""
    cell = (cell or "").strip()
    if cell in ("", "-", "—", "n/a", "N/A"):
        return []
    return [p.strip() for p in re.split(r"[,\s]+", cell) if p.strip()]


# ------------------------------------------------------------------- new


def render(template_name, values):
    with open(os.path.join(TEMPLATES, template_name)) as f:
        content = f.read()
    for token, value in values.items():
        content = content.replace(token, value)
    return content


def repo_prefixes(repos):
    """Short, unique task-ID prefixes derived from repo names.

    Repos are conventionally `ai-<slug>-<type>`, so the *trailing* segment is the
    distinctive one — `ai-kpi-etl` and `ai-kpi-api` share every leading segment and
    would otherwise all collapse to `AI`. Numeric suffix breaks any remaining tie.
    """
    out, seen = [], {}
    for repo in repos:
        segments = [s for s in re.split(r"[^A-Za-z0-9]+", repo) if s]
        base = (segments[-1] if segments else "TASK").upper()[:5]
        seen[base] = seen.get(base, 0) + 1
        out.append(base if seen[base] == 1 else f"{base}{seen[base]}")
    return out


def cmd_new(args):
    specs_root = resolve_specs_root(args.specs_root)
    number = args.number or next_number(specs_root)
    slug = args.slug.strip().lower()
    if not re.match(r"^[a-z0-9]+(-[a-z0-9]+)*$", slug):
        sys.exit(f"ERROR: slug must be kebab-case, got {slug!r}")

    feature_id = f"{number}-{slug}"
    feature_dir = os.path.join(specs_root, feature_id)
    if os.path.exists(feature_dir):
        sys.exit(f"ERROR: {feature_dir} already exists. Pick another slug.")

    repos = [r.strip() for r in (args.repos or "").split(",") if r.strip()]
    repo_rows = "\n".join(f"| {r} | TODO_SET_TYPE | TODO_SET_CHANGE |" for r in repos)
    if not repo_rows:
        repo_rows = "| TODO_SET_REPO | TODO_SET_TYPE | TODO_SET_CHANGE |"

    task_rows = "\n".join(
        f"| {prefix}-01 | {repo} | TODO_SET_TASK | FR-01 | TODO_SET_DAYS | P0 | - | TODO |"
        for prefix, repo in zip(repo_prefixes(repos), repos)
    )
    if not task_rows:
        task_rows = "| TODO-01 | TODO_SET_REPO | TODO_SET_TASK | FR-01 | TODO_SET_DAYS | P0 | - | TODO |"

    common = {
        "TPLVAR_ID": feature_id,
        "TPLVAR_TITLE": args.title,
        "TPLVAR_DATE": args.date or datetime.date.today().isoformat(),
        "TPLVAR_SYSTEM": args.system or load_profile().get("system", "TODO_SET_SYSTEM"),
        "TPLVAR_DESCRIPTION": args.description or "TODO_SET_DESCRIPTION",
        "TPLVAR_REPO_ROWS": repo_rows,
        "TPLVAR_TASK_ROWS": task_rows,
    }

    os.makedirs(feature_dir)
    for template, out in (("spec.md", "spec.md"), ("tasks.md", "tasks.md")):
        with open(os.path.join(feature_dir, out), "w") as f:
            f.write(render(template, common))

    print(f"Created {feature_dir}")
    print("  spec.md    requirements, design, contracts, decisions")
    print("  tasks.md   the source of truth for work")
    print(f"\nFeature ID: {feature_id}")
    if repos:
        print(f"Repos: {', '.join(repos)}")
    print(f"\nNext: fill spec.md, then /spec:plan {feature_id}")


# ----------------------------------------------------------------- check


class Report:
    def __init__(self):
        self.errors = []
        self.warnings = []

    def error(self, msg):
        self.errors.append(msg)

    def warn(self, msg):
        self.warnings.append(msg)


def detect_cycles(graph):
    """Return the first dependency cycle found, as a list of IDs, else None."""
    WHITE, GREY, BLACK = 0, 1, 2
    color = {n: WHITE for n in graph}
    stack = []

    def visit(node):
        color[node] = GREY
        stack.append(node)
        for dep in graph.get(node, []):
            if dep not in color:
                continue
            if color[dep] == GREY:
                return stack[stack.index(dep) :] + [dep]
            if color[dep] == WHITE:
                found = visit(dep)
                if found:
                    return found
        stack.pop()
        color[node] = BLACK
        return None

    for node in graph:
        if color[node] == WHITE:
            cycle = visit(node)
            if cycle:
                return cycle
    return None


def cmd_check(args):
    specs_root = resolve_specs_root(args.specs_root)
    feature_dir = args.feature
    if not os.path.isabs(feature_dir):
        candidate = os.path.join(specs_root, feature_dir)
        feature_dir = (
            candidate if os.path.isdir(candidate) else os.path.abspath(feature_dir)
        )
    if not os.path.isdir(feature_dir):
        sys.exit(f"ERROR: no feature directory at {feature_dir}")

    spec_path = os.path.join(feature_dir, "spec.md")
    tasks_path = os.path.join(feature_dir, "tasks.md")
    for p in (spec_path, tasks_path):
        if not os.path.isfile(p):
            sys.exit(f"ERROR: missing {p}")

    with open(spec_path) as f:
        spec_text = f.read()
    with open(tasks_path) as f:
        tasks_text = f.read()

    rpt = Report()
    spec_tables = parse_tables(spec_text)
    task_tables = parse_tables(tasks_text)

    # --- requirements
    req_table = find_table(spec_tables, "ID", "Requirement", "Acceptance criteria")
    requirements = {}
    if req_table is None:
        rpt.error(
            "spec.md has no Requirements table (needs ID | Requirement | Acceptance criteria)"
        )
    else:
        for row in req_table["rows"]:
            rid = row["ID"]
            if not REQ_ID.match(rid):
                rpt.error(
                    f"spec.md:{row['_line']} requirement ID {rid!r} is not FR-NN / NFR-NN"
                )
                continue
            requirements[rid] = row
            if (
                "TODO_SET_" in row["Acceptance criteria"]
                or not row["Acceptance criteria"]
            ):
                rpt.error(f"{rid} has no acceptance criteria")

    # --- repos
    repo_table = find_table(spec_tables, "Repo", "Type", "What changes here")
    declared_repos = set()
    if repo_table is not None:
        for row in repo_table["rows"]:
            if row["Repo"] and "TODO_SET_" not in row["Repo"]:
                declared_repos.add(row["Repo"])
    if not declared_repos:
        rpt.error("spec.md § Repos Touched lists no real repo")

    # --- decisions
    dec_table = find_table(spec_tables, "ID", "Decision", "Status")
    open_decisions = set()
    all_decisions = set()
    if dec_table is not None:
        for row in dec_table["rows"]:
            did = row["ID"]
            if not DEC_ID.match(did):
                continue
            all_decisions.add(did)
            if row["Status"].strip().upper() == "OPEN":
                open_decisions.add(did)
                if not row.get("Owner", "").strip():
                    rpt.error(f"{did} is OPEN with no owner")

    # --- tasks
    task_table = find_table(
        task_tables, "ID", "Repo", "Days", "Priority", "Depends", "Status"
    )
    tasks = {}
    if task_table is None:
        rpt.error(
            "tasks.md has no task table (needs ID | Repo | Task | Covers | Days | Priority | Depends | Status)"
        )
    else:
        for row in task_table["rows"]:
            tid = row["ID"].strip()
            if not tid or "TPLVAR" in tid:
                continue
            if tid in tasks:
                rpt.error(f"tasks.md:{row['_line']} duplicate task ID {tid}")
            tasks[tid] = row

    covered = set()
    graph = {}
    total_days = 0.0
    done_days = 0.0
    by_repo = {}
    by_priority = {}

    for tid, row in tasks.items():
        line = row["_line"]

        raw_days = row["Days"].strip()
        try:
            days = float(raw_days)
        except ValueError:
            rpt.error(f"tasks.md:{line} {tid} Days is not a number: {raw_days!r}")
            days = 0.0
        else:
            if days > MAX_DAYS:
                rpt.error(
                    f"{tid} is {days} days — over the {MAX_DAYS}-day cap. "
                    f"Split it along a real seam ({tid}a / {tid}b)."
                )
            if days <= 0:
                rpt.error(f"{tid} has {days} days")

        priority = row["Priority"].strip().upper()
        if priority not in PRIORITIES:
            rpt.error(f"{tid} priority {priority!r} is not one of {sorted(PRIORITIES)}")

        status = row["Status"].strip().upper()
        if status not in STATUSES:
            rpt.error(f"{tid} status {status!r} is not one of {sorted(STATUSES)}")

        repo = row["Repo"].strip()
        if declared_repos and repo not in declared_repos:
            rpt.error(
                f"{tid} names repo {repo!r} which is not in spec.md § Repos Touched"
            )

        for cid in split_ids(row.get("Covers")):
            if requirements and cid not in requirements:
                rpt.error(f"{tid} Covers {cid} which does not exist in spec.md")
            covered.add(cid)

        deps = split_ids(row.get("Depends"))
        task_deps = []
        for dep in deps:
            if DEC_ID.match(dep):
                if dep not in all_decisions:
                    rpt.error(
                        f"{tid} depends on decision {dep} which is not in spec.md"
                    )
                elif dep in open_decisions and status in ("WIP", "DONE"):
                    rpt.error(f"{tid} is {status} but decision {dep} is still OPEN")
                continue
            if dep == tid:
                rpt.error(f"{tid} depends on itself")
                continue
            if dep not in tasks:
                rpt.error(f"{tid} depends on {dep} which is not a task")
                continue
            task_deps.append(dep)
        graph[tid] = task_deps

        total_days += days
        if status == "DONE":
            done_days += days
        by_repo.setdefault(repo, [0.0, 0.0])
        by_repo[repo][0] += days
        if status == "DONE":
            by_repo[repo][1] += days
        by_priority[priority] = by_priority.get(priority, 0.0) + days

    # a DONE task whose dependency is not DONE is a real ordering violation
    for tid, deps in graph.items():
        if tasks[tid]["Status"].strip().upper() != "DONE":
            continue
        for dep in deps:
            if tasks[dep]["Status"].strip().upper() != "DONE":
                rpt.error(f"{tid} is DONE but its dependency {dep} is not")

    cycle = detect_cycles(graph)
    if cycle:
        rpt.error("dependency cycle: " + " -> ".join(cycle))

    uncovered = sorted(set(requirements) - covered)
    for rid in uncovered:
        rpt.error(f"{rid} is not covered by any task (no task lists it under Covers)")

    repos_without_tasks = sorted(
        declared_repos - {t["Repo"].strip() for t in tasks.values()}
    )
    for repo in repos_without_tasks:
        rpt.error(f"repo {repo!r} is listed in spec.md but has no task")

    for did in sorted(open_decisions):
        blocked = [t for t, r in tasks.items() if did in split_ids(r.get("Depends"))]
        if blocked:
            rpt.warn(f"{did} is OPEN and blocks {', '.join(sorted(blocked))}")
        else:
            rpt.warn(
                f"{did} is OPEN and no task is waiting on it — is it still relevant?"
            )

    leftover = len(re.findall(r"TODO_SET_\w+", spec_text)) + len(
        re.findall(r"TODO_SET_\w+", tasks_text)
    )
    if leftover:
        rpt.warn(f"{leftover} TODO_SET_ placeholder(s) still unfilled")

    # ------------------------------------------------------------- output
    name = os.path.basename(feature_dir)
    print(f"=== {name} ===\n")

    if tasks:
        pct = (done_days / total_days * 100) if total_days else 0.0
        done_n = sum(1 for t in tasks.values() if t["Status"].strip().upper() == "DONE")
        print(f"Tasks      {done_n}/{len(tasks)} done")
        print(f"Effort     {done_days:g}/{total_days:g} man-days ({pct:.0f}%)")
        p0 = by_priority.get("P0", 0.0)
        print(f"P0         {p0:g} days")
        print()
        print(f"{'Repo':<28} {'Days':>7} {'Done':>7}")
        for repo in sorted(by_repo):
            tot, dn = by_repo[repo]
            print(f"{repo:<28} {tot:>7g} {dn:>7g}")
        print()
        print(f"{'Priority':<28} {'Days':>7}")
        for pr in sorted(by_priority):
            print(f"{pr:<28} {by_priority[pr]:>7g}")
        print()

    if requirements:
        print(
            f"Requirements covered: {len(set(requirements) & covered)}/{len(requirements)}"
        )
        print()

    for w in rpt.warnings:
        print(f"WARN   {w}")
    for e in rpt.errors:
        print(f"ERROR  {e}")

    print()
    if rpt.errors:
        print(f"FAIL — {len(rpt.errors)} error(s), {len(rpt.warnings)} warning(s)")
        return 1
    if tasks and done_days >= total_days and total_days > 0:
        print(f"COMPLETE — every task DONE, {len(requirements)} requirement(s) covered")
    else:
        print(f"OK — {len(rpt.warnings)} warning(s), no structural errors")
    return 0


# ------------------------------------------------------------------- cli


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument(
        "--specs-root", help="override specs root (else $SPEC_ROOT, profile, ./specs)"
    )
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_new = sub.add_parser("new", help="create a feature spec")
    p_new.add_argument("--slug", required=True, help="kebab-case identifier")
    p_new.add_argument("--title", required=True, help="human-readable title")
    p_new.add_argument("--description", help="one paragraph")
    p_new.add_argument(
        "--repos", help="comma-separated repo names this feature touches"
    )
    p_new.add_argument("--system", help="system name (else profile, else placeholder)")
    p_new.add_argument("--number", help="force a feature number (else next sequential)")
    p_new.add_argument("--date", help="ISO date (else today)")
    p_new.set_defaults(func=cmd_new)

    p_check = sub.add_parser("check", help="validate a feature spec + tasks")
    p_check.add_argument(
        "feature", help="feature id or directory, e.g. 001-kpi-reporting"
    )
    p_check.set_defaults(func=cmd_check)

    args = ap.parse_args()
    sys.exit(args.func(args) or 0)


if __name__ == "__main__":
    main()
