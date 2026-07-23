"""Deploy the Genie space from its source-of-truth files.

Builds the `serialized_space` payload from genie-space/space.yml and calls the
Genie management API: createspace when space_id is empty, else updatespace. With
--apply-ddl it first runs views/*.sql and functions/*.sql on the space warehouse.

Auth: uses the default Databricks SDK auth chain (DATABRICKS_HOST + token, or a
CLI profile). Run locally via ./deploy.sh, or in CI (see .gitlab-ci.yml).

NOTE: the Genie management API is recent (Public Preview). Verify the exact SDK
method / payload field names against the docs for your workspace version:
https://docs.databricks.com/api/workspace/genie/createspace
"""

import argparse
import glob
import json
import os

import yaml
from databricks.sdk import WorkspaceClient


def _read_rel(root, name):
    """Read a prose file referenced by space.yml (relative to space.yml)."""
    if not name:
        return ""
    with open(os.path.join(root, name), encoding="utf-8") as f:
        return f.read()


def _read_example_queries(root, name):
    """Load curated question->SQL pairs from example_queries.yml if referenced and
    present. Returns [] when the file is missing or its list is empty, so the
    payload only carries example queries when the author actually provided some."""
    if not name:
        return []
    path = os.path.join(root, name)
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        doc = yaml.safe_load(f) or {}
    return [
        {"question": e["question"], "query": e["sql"]}
        for e in (doc.get("example_queries") or [])
    ]


def build_serialized_space(space, root):
    """Map space.yml (+ its referenced prose / example files) → the serialized_space
    JSON the API expects (version 2)."""
    payload = {
        "version": 2,
        "title": space["title"],
        "description": _read_rel(root, space.get("description_file")),
        "instructions": _read_rel(root, space.get("instructions_file")),
        "data_sources": space.get("data_sources", {"tables": [], "metric_views": []}),
        "sample_questions": [
            {"id": f"{i:032x}", "question": [q]}
            for i, q in enumerate(space.get("sample_questions", []))
        ],
    }
    # Curated example SQL queries are optional — only include the field when the
    # author supplied entries. Confirm the exact payload field name for your
    # workspace (Public Preview); see docs/GENIE_STANDARDS.md §3, §6.
    example_queries = _read_example_queries(root, space.get("example_queries_file"))
    if example_queries:
        payload["example_queries"] = example_queries
    return payload


def apply_ddl(w, warehouse_id, root):
    for sql_file in sorted(glob.glob(os.path.join(root, "views", "*.sql")) +
                           glob.glob(os.path.join(root, "functions", "*.sql"))):
        print(f"==> applying {sql_file}")
        w.statement_execution.execute_statement(
            warehouse_id=warehouse_id, statement=open(sql_file).read()
        )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--space", default="genie-space/space.yml")
    ap.add_argument("--apply-ddl", action="store_true")
    args = ap.parse_args()

    root = os.path.dirname(args.space)
    space = yaml.safe_load(open(args.space))
    w = WorkspaceClient()

    if args.apply_ddl:
        apply_ddl(w, space["warehouse_id"], root)

    payload = build_serialized_space(space, root)
    serialized = json.dumps(payload)

    # TODO: confirm SDK method names for your workspace (w.genie.*). Fallback:
    #       call the REST API directly (POST /api/2.0/genie/spaces).
    if space.get("space_id"):
        print(f"==> updating Genie space {space['space_id']}")
        # w.genie.update_space(space_id=space["space_id"], serialized_space=serialized)
    else:
        print("==> creating new Genie space")
        # resp = w.genie.create_space(serialized_space=serialized,
        #                             warehouse_id=space["warehouse_id"])
        # space["space_id"] = resp.space_id
        # yaml.safe_dump(space, open(args.space, "w"), sort_keys=False)
        # print(f"    wrote new space_id={resp.space_id} back to {args.space}")

    print("==> done (uncomment the API calls once method/fields are confirmed)")


if __name__ == "__main__":
    main()
