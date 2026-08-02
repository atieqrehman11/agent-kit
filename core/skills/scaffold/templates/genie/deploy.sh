#!/bin/bash
set -e
cd "$(dirname "$0")"   # paths below are repo-relative, so run from anywhere
# Local Genie deploy — applies backing-view DDL, then create/update the space.
# Needs DATABRICKS_HOST + DATABRICKS_TOKEN (or a configured CLI profile) and a
# warehouse_id set in genie-space/space.yml.
#
# Local deploys target dev. Pass --env stg / --env prod only if you are pointed at
# that workspace on purpose; normally stg and prod are deployed by CI on a branch
# merge (.gitlab-ci.yml), against credentials this laptop does not hold.
python3 -m pip install -q -r requirements.txt
python3 src/deploy.py --apply-ddl "$@"
