#!/bin/bash
set -e
# Local Genie deploy — applies backing-view DDL, then create/update the space.
# Needs DATABRICKS_HOST + DATABRICKS_TOKEN (or a configured CLI profile) and a
# warehouse_id set in genie-space/space.yml.
python3 -m pip install -q -r requirements.txt
python3 deploy_genie.py --space genie-space/space.yml --apply-ddl
