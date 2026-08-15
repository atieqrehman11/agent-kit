"""Build serialized_space from genie-space/space.yml and reconcile the space.

The space is identified by title, "<title> [ENV]", in the workspace the SDK
authenticated to — no id is stored in the repo. See docs/GENIE_STANDARDS.md §4.

    ./deploy.sh                     # dev, applies views/ + functions/ DDL first
    ./deploy.sh --env stg

The Genie management API is Public Preview; payload fields may move:
https://docs.databricks.com/api/workspace/genie/createspace
"""

import argparse
import glob
import json
import os

import yaml
from databricks.sdk import WorkspaceClient
from validate import check

ENVS = ("dev", "stg", "prod")


def _read_rel(root, name):
    """Read a prose file referenced by space.yml (relative to space.yml)."""
    if not name:
        return ""
    with open(os.path.join(root, name), encoding="utf-8") as f:
        return f.read()


def _read_example_queries(root, name):
    """Curated question->SQL pairs, or [] when the file is absent or its list empty."""
    if not name:
        return []
    path = os.path.join(root, name)
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        doc = yaml.safe_load(f) or {}
    return [
        {"question": e["question"], "query": e["sql"]} for e in (doc.get("example_queries") or [])
    ]


def target_title(title, env):
    """Every environment is suffixed, prod included — one rule, no exception."""
    return f"{title} [{env.upper()}]"


def build_serialized_space(space, root, title):
    """space.yml + its prose files -> the serialized_space payload (version 2)."""
    payload = {
        "version": 2,
        "title": title,
        "description": _read_rel(root, space.get("description_file")),
        "instructions": _read_rel(root, space.get("instructions_file")),
        "data_sources": space.get("data_sources", {"tables": [], "metric_views": []}),
        "sample_questions": [
            {"id": f"{i:032x}", "question": [q]}
            for i, q in enumerate(space.get("sample_questions", []))
        ],
    }
    # Optional — send the field only when there are entries (see GENIE_STANDARDS §6).
    example_queries = _read_example_queries(root, space.get("example_queries_file"))
    if example_queries:
        payload["example_queries"] = example_queries
    return payload


def resolve_existing(w, title):
    """The space with this title, or None. Refuses on duplicates."""
    matches, token = [], None
    while True:
        page = w.genie.list_spaces(page_token=token)
        matches += [s for s in (page.spaces or []) if s.title == title]
        token = page.next_page_token
        if not token:
            break
    if len(matches) > 1:
        raise SystemExit(
            f"{len(matches)} Genie spaces in this workspace are titled {title!r}. "
            "Deploy refuses to guess which one is this repo's — delete or rename "
            "the extras."
        )
    return matches[0] if matches else None


def apply_ddl(w, warehouse_id, root):
    for sql_file in sorted(
        glob.glob(os.path.join(root, "views", "*.sql"))
        + glob.glob(os.path.join(root, "functions", "*.sql"))
    ):
        print(f"==> applying {sql_file}")
        w.statement_execution.execute_statement(
            warehouse_id=warehouse_id, statement=open(sql_file).read()
        )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--space", default="genie-space/space.yml")
    ap.add_argument("--apply-ddl", action="store_true")
    ap.add_argument(
        "--env",
        default="dev",
        choices=ENVS,
        help="target environment — the title suffix; the workspace comes from "
        "DATABRICKS_HOST / the CLI profile",
    )
    args = ap.parse_args()

    problems = check(args.space)
    if problems:
        raise SystemExit("\n".join([f"ERROR: {p}" for p in problems] + ["Refusing to deploy."]))

    root = os.path.dirname(args.space)
    space = yaml.safe_load(open(args.space))
    w = WorkspaceClient()

    title = target_title(space["title"], args.env)
    print(f"==> target {title!r} in {w.config.host}")

    if args.apply_ddl:
        apply_ddl(w, space["warehouse_id"], root)

    serialized = json.dumps(build_serialized_space(space, root, title))

    existing = resolve_existing(w, title)
    if existing:
        print(f"==> updating Genie space {existing.space_id}")
        deployed = w.genie.update_space(
            space_id=existing.space_id,
            title=title,
            serialized_space=serialized,
            warehouse_id=space["warehouse_id"],
        )
    else:
        print("==> creating Genie space (no existing one with that title)")
        deployed = w.genie.create_space(
            warehouse_id=space["warehouse_id"],
            serialized_space=serialized,
            title=title,
        )

    print("==> deployed")
    print(f"    env:      {args.env}")
    print(f"    space id: {deployed.space_id}")
    print(f"    open:     {w.config.host.rstrip('/')}/genie/rooms/{deployed.space_id}")


if __name__ == "__main__":
    main()
