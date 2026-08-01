"""TPLVAR_DISPLAY_NAME — job entrypoint.

Run as a Databricks job task (spark_python_task). Reads the per-environment
config file that the resource passes via --config (config/DEV|STG|PROD).
Implement the domain logic in run().
"""

import argparse
import sys


def parse_args(argv):
    parser = argparse.ArgumentParser(description="TPLVAR_DISPLAY_NAME job")
    parser.add_argument("--config", required=True, help="Path to task_config.yaml")
    return parser.parse_args(argv)


def load_config(path):
    import yaml

    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def run(config):
    # TODO: implement the job. `config` holds env, catalog, table_prefix, etc.
    print(
        f"Running TPLVAR_SLUG job in {config.get('env')} "
        f"(catalog={config.get('catalog')}, prefix={config.get('table_prefix')})"
    )


def main(argv=None):
    args = parse_args(argv if argv is not None else sys.argv[1:])
    run(load_config(args.config))


if __name__ == "__main__":
    main()
