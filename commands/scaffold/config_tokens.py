"""Shared registry of ``TODO_SET_*`` configuration placeholders.

Used by:
  - ``new.py``       to emit ``CONFIG.md`` (only the tokens a repo actually contains)
  - ``configure.py`` to group the sheet and apply filled values across the tree

Each entry is ``(token, group, label, example)``. Order here is the order tokens
appear in ``CONFIG.md``; groups are emitted in first-seen order. Any token found
in a repo but missing here still shows up under an "Other" group, so the sheet is
never silently incomplete.
"""

TOKENS = [
    # token, group, label, example
    (
        "TODO_SET_TEAM_NAME",
        "Team & Ownership",
        "Team name (hyphenated) — CI registration + job alerts",
        "<your-team>",
    ),
    (
        "TODO_SET_TEAM_EMAIL",
        "Team & Ownership",
        "Team email — job failure alerts",
        "team@example.com",
    ),
    (
        "TODO_SET_OWNER",
        "Team & Ownership",
        "Service owner shown in GET /v1/info",
        "Analytics",
    ),
    (
        "TODO_SET_SUPPORT_EMAIL",
        "Team & Ownership",
        "Support email shown in GET /v1/info",
        "support@example.com",
    ),
    (
        "TODO_SET_REPO_URL",
        "Repository",
        "GitLab repo URL — controller registration",
        "https://gitlab.com/<group>/my-service",
    ),
    (
        "TODO_SET_CONTROLLER_REPO_URL",
        "CI/CD",
        "Shared DAB CI/CD controller repo URL (stg/prod deploys)",
        "https://gitlab.com/<group>/databricks-asset-bundle-ci-cd-controller",
    ),
    (
        "TODO_SET_CI_IMAGE",
        "CI/CD",
        "CI container image with the Databricks CLI/SDK",
        "<registry>/databricks-ci:latest",
    ),
    (
        "TODO_SET_GITLAB_RUNNER",
        "CI/CD",
        "GitLab runner tag for CI jobs",
        "my-ci-runner",
    ),
    (
        "TODO_SET_CONTROLLER_PROJECT_ID",
        "CI/CD",
        "Numeric GitLab project id of the CI/CD controller",
        "1234567",
    ),
    (
        "TODO_SET_DEV_WORKSPACE_HOST",
        "Databricks Workspaces",
        "Dev workspace host — local (./bundle.sh) deploy target",
        "https://<workspace>-dev.cloud.databricks.com",
    ),
    (
        "TODO_SET_STG_WORKSPACE_HOST",
        "Databricks Workspaces",
        "Staging workspace host — CI deploy on merge to stg",
        "https://<workspace>-stg.cloud.databricks.com",
    ),
    (
        "TODO_SET_PROD_WORKSPACE_HOST",
        "Databricks Workspaces",
        "Production workspace host — CI deploy on merge to prod",
        "https://<workspace>-prod.cloud.databricks.com",
    ),
    (
        "TODO_SET_STG_SERVICE_PRINCIPAL",
        "Service Principals",
        "Staging run-as service principal (name)",
        "",
    ),
    (
        "TODO_SET_PROD_SERVICE_PRINCIPAL",
        "Service Principals",
        "Production run-as service principal (name)",
        "",
    ),
    (
        "TODO_SET_STG_SP_ID",
        "Service Principals",
        "Staging service principal application id",
        "",
    ),
    (
        "TODO_SET_PROD_SP_ID",
        "Service Principals",
        "Production service principal application id",
        "",
    ),
    ("TODO_SET_POLICY_ID", "Cluster Policy IDs", "Controller cluster policy id", ""),
    ("TODO_SET_DEV_POLICY_ID", "Cluster Policy IDs", "Dev cluster policy id", ""),
    ("TODO_SET_STG_POLICY_ID", "Cluster Policy IDs", "Staging cluster policy id", ""),
    (
        "TODO_SET_PROD_POLICY_ID",
        "Cluster Policy IDs",
        "Production cluster policy id",
        "",
    ),
    ("TODO_SET_CATALOG", "Data", "Unity Catalog", "my_catalog_dev"),
    ("TODO_SET_TABLE_PREFIX", "Data", "snake_case table name prefix", "myapp_"),
    (
        "TODO_SET_DEVELOPERS_GROUP",
        "Permissions",
        "Workspace group granted CAN_MANAGE on the app",
        "<workspace>-developers-dev",
    ),
    (
        "TODO_SET_PROD_ADMIN_USER",
        "Permissions",
        "Human owner granted CAN_MANAGE in prod (databricks.yml)",
        "you@example.com",
    ),
    (
        "TODO_SET_FRONTEND_SP_ID",
        "Permissions",
        "Frontend app service-principal id granted CAN_USE on the API",
        "",
    ),
    (
        "TODO_SET_WAREHOUSE_ID",
        "API Runtime",
        "SQL warehouse id — gold-layer panel queries",
        "",
    ),
    (
        "TODO_SET_CHAT_GATEWAY_URL",
        "API Runtime",
        "Shared chat gateway base URL (ai-prototype-chat-api)",
        "",
    ),
    (
        "TODO_SET_GENIE_SPACE_ID",
        "API Runtime",
        "Genie space id (only if the app queries Genie)",
        "",
    ),
]

# token -> (token, group, label, example)
META = {t[0]: t for t in TOKENS}
