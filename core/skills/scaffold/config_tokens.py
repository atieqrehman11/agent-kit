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
        "TODO_SET_DESCRIPTION",
        "Service Identity",
        "One-sentence description of the service — shown in GET /v1/info",
        "KPI reporting, anomaly summaries, and report generation.",
    ),
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
        "Dev workspace host — local (./run_local.sh deploy) deploy target",
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
        "TODO_SET_STG_CATALOG",
        "Data",
        "Unity Catalog in the STAGING workspace",
        "myapp_stg",
    ),
    (
        "TODO_SET_PROD_CATALOG",
        "Data",
        "Unity Catalog in the PRODUCTION workspace",
        "myapp_prod",
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
        "TODO_SET_STG_SOURCE_VOLUME",
        "Data",
        "Volume path the STAGING pipeline reads",
        "/Volumes/<catalog>/bronze/unstructured_data/<folder>/",
    ),
    (
        "TODO_SET_PROD_SOURCE_VOLUME",
        "Data",
        "Volume path the PRODUCTION pipeline reads",
        "/Volumes/<catalog>/bronze/unstructured_data/<folder>/",
    ),
    (
        "TODO_SET_DEVELOPERS_GROUP",
        "Permissions",
        "Workspace group granted CAN_MANAGE on the app",
        "<workspace>-developers-dev",
    ),
    (
        "TODO_SET_STG_DEVELOPERS_GROUP",
        "Permissions",
        "Workspace group granted CAN_MANAGE in STAGING",
        "<workspace>-developers-stg",
    ),
    (
        "TODO_SET_PROD_DEVELOPERS_GROUP",
        "Permissions",
        "Workspace group granted CAN_RUN in PRODUCTION",
        "<workspace>-developers",
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
        "TODO_SET_STG_FRONTEND_SP_ID",
        "Permissions",
        "Frontend app service-principal id in STAGING — a different id from dev's, "
        "because each workspace mints the app its own",
        "",
    ),
    (
        "TODO_SET_PROD_FRONTEND_SP_ID",
        "Permissions",
        "Frontend app service-principal id in PRODUCTION",
        "",
    ),
    (
        "TODO_SET_WAREHOUSE_ID",
        "API Runtime",
        "SQL warehouse id — gold-layer queries (dev)",
        "",
    ),
    (
        "TODO_SET_STG_WAREHOUSE_ID",
        "API Runtime",
        "SQL warehouse id in the STAGING workspace",
        "",
    ),
    (
        "TODO_SET_PROD_WAREHOUSE_ID",
        "API Runtime",
        "SQL warehouse id in the PRODUCTION workspace",
        "",
    ),
    (
        "TODO_SET_FRONTEND_ORIGIN",
        "API Runtime",
        "Allowed CORS origin — the frontend that calls this API. Never *",
        "https://app.example.com",
    ),
    (
        "TODO_SET_STG_FRONTEND_ORIGIN",
        "API Runtime",
        "Allowed CORS origin in STAGING",
        "https://<app>-<workspace-id>.aws.databricksapps.com",
    ),
    (
        "TODO_SET_PROD_FRONTEND_ORIGIN",
        "API Runtime",
        "Allowed CORS origin in PRODUCTION",
        "https://app.example.com",
    ),
    (
        "TODO_SET_CHAT_GATEWAY_URL",
        "API Runtime",
        "Shared chat gateway base URL (the conversational API service)",
        "",
    ),
    (
        "TODO_SET_GENIE_SPACE_ID",
        "Agent Tools",
        "Genie space id attached as an agent tool. Workspace-local, so it differs "
        "per environment — the dev value is never valid in stg",
        "",
    ),
    (
        "TODO_SET_STG_GENIE_SPACE_ID",
        "Agent Tools",
        "Genie space id in the STAGING workspace",
        "",
    ),
    (
        "TODO_SET_PROD_GENIE_SPACE_ID",
        "Agent Tools",
        "Genie space id in the PRODUCTION workspace",
        "",
    ),
    (
        "TODO_SET_VECTOR_SEARCH_INDEX",
        "Agent Tools",
        "Vector Search index attached as an agent tool, <catalog>.<schema>.<index>",
        "",
    ),
    (
        "TODO_SET_STG_VECTOR_SEARCH_INDEX",
        "Agent Tools",
        "Vector Search index in the STAGING workspace",
        "",
    ),
    (
        "TODO_SET_PROD_VECTOR_SEARCH_INDEX",
        "Agent Tools",
        "Vector Search index in the PRODUCTION workspace",
        "",
    ),
    (
        "TODO_SET_STG_BACKEND_API_URL",
        "Front End Runtime",
        "Use case API the front end proxies to in STAGING",
        "https://<app-name>-<workspace-id>.aws.databricksapps.com",
    ),
    (
        "TODO_SET_PROD_BACKEND_API_URL",
        "Front End Runtime",
        "Use case API the front end proxies to in PRODUCTION",
        "https://<app-name>-<workspace-id>.aws.databricksapps.com",
    ),
    (
        "TODO_SET_BACKEND_API_URL",
        "Front End Runtime",
        "Use case API the front end proxies to. The browser never sees it — it "
        "calls the same-origin /api path and server.mjs forwards",
        "https://<app-name>.<workspace>.databricksapps.com",
    ),
]

# token -> (token, group, label, example)
META = {t[0]: t for t in TOKENS}
