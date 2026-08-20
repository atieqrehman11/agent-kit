"""Build the serialized Genie space from the versioned sources under src/.

    python python/build_space.py --env dev

src/{space.yml, instructions.md, data_sources.yml, sql_functions.yml,
example_queries.yml} -> generated/space.<env>.json, which resources/genie.yml
deploys. Nothing here talks to Databricks: reconciling the space is
`databricks bundle deploy`, run by ./run_local.sh for dev and by the CI/CD
controller for stg and prod.

The catalog is baked in at build time, so there is one artifact per environment —
DAB resolves ${var.*} inside an inline serialized_space, but NOT inside the file
named by file_path.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import uuid

import yaml

ENVS = ("dev", "stg", "prod")

# What the BUILD substitutes. title and warehouse_id are deploy-time fields DAB
# reads from databricks.yml, so they do not gate building an artifact.
REQUIRED_ENV_KEYS = ("catalog", "schema")


def _read_prose(root, name):
    """A prose file referenced by space.yml, sent BYTE-VERBATIM.

    Nothing is stripped or normalised: the payload is compared byte for byte on
    the next deploy, so a reflow or a "tidy" here turns a no-op deploy into a
    content change. .editorconfig stops editors adding a trailing newline.
    """
    if not name:
        return ""
    with open(os.path.join(root, name), encoding="utf-8") as f:
        return f.read()


def _lines(text):
    """A string as the API represents it: a list of lines, newlines kept."""
    return text.splitlines(keepends=True)


def _with_id(entry, source):
    """Carry the entry's id across when the source file records one.

    Preserving the id makes an update EDIT the existing entry. Omitting it makes
    the API drop the old one and add a new one under a fresh id — same text, but
    every curated-question and eval reference to it breaks.
    """
    if source.get("id"):
        return {"id": source["id"], **entry}
    return entry


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
        _with_id({"question": _lines(e["question"]), "sql": _lines(e["sql"])}, e)
        for e in (doc.get("example_queries") or [])
    ]


def env_from_bundle(env, path="databricks.yml"):
    """Per-environment values, read from databricks.yml — the one place they live.

    Target overrides beat the variable default, which is exactly how DAB resolves
    them, so the artifact is built from the same values the deploy will use.
    """
    with open(path, encoding="utf-8") as f:
        doc = yaml.safe_load(f) or {}
    target = (doc.get("targets") or {}).get(env)
    if target is None:
        raise SystemExit(f"{path}: no target {env!r}")

    out = {}
    for key in REQUIRED_ENV_KEYS:
        value = (target.get("variables") or {}).get(key)
        if value is None:
            value = ((doc.get("variables") or {}).get(key) or {}).get("default")
        out[key] = value

    missing = [k for k, v in out.items() if not v]
    if missing:
        raise SystemExit(f"{path}: target {env} has no {', '.join(missing)}")
    unresolved = [k for k, v in out.items() if str(v).startswith("TODO_SET_")]
    if unresolved:
        raise SystemExit(
            f"{path}: target {env} still has placeholder {', '.join(unresolved)} — "
            "fill it in (CONFIG.md) before building."
        )
    return out


def substitute(text, env_config):
    """Expand ${catalog} / ${schema} for the target environment.

    Applied to everything that reaches the workspace: the payload identifiers, the
    example SQL, and the DDL under views/ and functions/. Nothing in src/ names a
    catalog literally, so there is no path by which a stg deploy reads dev.
    """
    return text.replace("${catalog}", env_config["catalog"]).replace(
        "${schema}", env_config["schema"]
    )


def build_serialized_space(space, root, env_config):
    """src/ -> the serialized_space payload (version 2).

    `title` and `description` are NOT in here — the API takes them as separate
    fields, so they live in resources/genie.yml.
    """
    instructions = {}

    text = _read_prose(root, space.get("instructions_file"))
    if text:
        instructions["text_instructions"] = [
            _with_id(
                {"content": _lines(substitute(text, env_config))},
                {"id": space.get("instructions_id")},
            )
        ]

    example_queries = _read_example_queries(root, space.get("example_queries_file"))
    if example_queries:
        instructions["example_question_sqls"] = [
            {
                **pair,
                "question": [substitute(ln, env_config) for ln in pair["question"]],
                "sql": [substitute(ln, env_config) for ln in pair["sql"]],
            }
            for pair in example_queries
        ]

    # The UC functions Genie may call. Omitting these DETACHES every one of them
    # on the first update — they are part of the payload, not a separate resource.
    functions = space.get("sql_functions") or []
    if functions:
        instructions["sql_functions"] = [
            _with_id({"identifier": substitute(f["identifier"], env_config)}, f)
            for f in functions
        ]

    payload = {
        "version": 2,
        "data_sources": {
            "tables": [
                {
                    "identifier": substitute(t["identifier"], env_config),
                    "column_configs": t.get("column_configs", []),
                }
                for t in (space.get("data_sources") or {}).get("tables", [])
            ]
        },
    }
    if instructions:
        payload["instructions"] = instructions
    return payload


def mint_missing_ids(root="src"):
    """Give every entry an id, writing it back into the source file.

    The API rejects a create without one — "id must be provided and non-empty.
    Expected lowercase 32-hex UUID without hyphens" — and it stores whatever we
    send, so ids are authored here rather than captured from the platform
    afterwards. Keeping them in git is what makes a redeploy update each entry in
    place instead of dropping and re-adding it.

    Text insertion, not a YAML round-trip: these files carry comments and
    byte-exact block scalars that a re-dump would silently reflow.
    """
    added = []
    for name in ("example_queries.yml", "sql_functions.yml"):
        path = os.path.join(root, name)
        if not os.path.exists(path):
            continue
        lines = open(path, encoding="utf-8").read().split("\n")
        # Item starts are `- ` at the list's indent; a block runs to the next one.
        starts = [i for i, ln in enumerate(lines) if re.match(r"^\s*- ", ln)]
        for n, i in enumerate(reversed(starts)):
            end = starts[len(starts) - n] if n else len(lines)
            block = lines[i:end]
            if any(re.match(r"^\s*(- )?id:\s*\S", ln) for ln in block):
                continue
            indent = " " * (len(lines[i]) - len(lines[i].lstrip()) + 2)
            new_id = uuid.uuid4().hex
            # After the last non-blank line of the block, so block scalars stay intact.
            last = max(j for j in range(i, end) if lines[j].strip())
            lines.insert(last + 1, f"{indent}id: {new_id}")
            added.append(f"{name}: minted {new_id}")
        open(path, "w", encoding="utf-8").write("\n".join(lines))

    path = os.path.join(root, "space.yml")
    space = {}
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            space = yaml.safe_load(f) or {}
    if not str(space.get("instructions_id") or "").strip():
        new_id = uuid.uuid4().hex
        with open(path, "a", encoding="utf-8") as f:
            f.write(f"instructions_id: {new_id}\n")
        added.append(f"space.yml: minted {new_id}")

    for line in added:
        print(f"  + {line}")
    return added


def load_space(root="src"):
    """space.yml plus the files it points at, merged into one declaration.

    Every kind of content lives in its own file — prose, examples, tables,
    functions — and space.yml is the manifest naming them. Callers see the
    combined shape, so nothing downstream knows about the split.
    """
    path = os.path.join(root, "space.yml")
    space = {}
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            space = yaml.safe_load(f) or {}

    # Filenames are convention, not configuration: a manifest listing them can
    # disagree with the tree, and there is nothing to decide.
    space["instructions_file"] = "instructions.md"
    space["example_queries_file"] = "example_queries.yml"

    for name, target in (
        ("data_sources.yml", "data_sources"),
        ("sql_functions.yml", "sql_functions"),
    ):
        f = os.path.join(root, name)
        if not os.path.exists(f):
            raise SystemExit(
                f"{f} is missing — the space would deploy with no {target}"
            )
        with open(f, encoding="utf-8") as handle:
            loaded = yaml.safe_load(handle) or {}
        if target not in loaded:
            raise SystemExit(f"{f}: expected a top-level {target!r} key")
        space[target] = loaded[target]
    return space


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--env", default="dev", choices=ENVS)
    ap.add_argument("--root", default="src")
    args = ap.parse_args()

    mint_missing_ids(args.root)
    space = load_space(args.root)
    env_config = env_from_bundle(args.env)

    payload = build_serialized_space(space, args.root, env_config)
    os.makedirs("generated", exist_ok=True)
    out = os.path.join("generated", f"space.{args.env}.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
        f.write("\n")

    ins = payload.get("instructions", {})
    counts = ", ".join(
        f"{k}={len(v) if isinstance(v, list) else 1}" for k, v in ins.items()
    )
    print(f"built {out}  (catalog={env_config['catalog']}, {counts})")


if __name__ == "__main__":
    main()
