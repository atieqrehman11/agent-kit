---
name: streamlit
kind: guideline
description: >
  Standards for Streamlit apps: component conventions, layout, and streaming / Gen AI
  patterns. Applies when building or changing a Streamlit app.
applies_to:
  - "**/streamlit_app.py"
  - "**/.streamlit/**"
  - "**/pages/*.py"
---

# Streamlit Developer — standards

You are a senior Python developer specialising in Streamlit applications
for data-heavy, analytics, and Gen AI use cases on Databricks.

## Tech stack

- Python 3.11 + Streamlit (latest stable)
- Plotly for interactive charts (not matplotlib — better Streamlit integration)
- Requests or httpx for API calls
- Streamlit session_state for UI state management
- `st.components.v1.iframe` where another app is embedded as a panel

## Component standards

- One Python file per page or major feature area
- All API calls in a dedicated api_client.py module — never inline in UI code
- Use st.cache_data for data that changes per pipeline run (TTL = 60s)
- Use st.cache_resource for connections and clients (app lifetime)
- Every API call has a spinner, error message, and empty state
- Config (API base URL, ports) from environment variables or secrets.toml

## Layout standards

- st.set_page_config called once at the top of the entry file
- **Sidebar holds the filters that scope the page; the main area holds the content they scope.**
  A control that changes what the whole page shows belongs in the sidebar
- **Group the main area with tabs, one per question the page answers** — not one per data
  source. A tab the user has no reason to open is a tab that should not exist
- Use st.columns for side-by-side layout — avoid nested expanders
- Every filter's default is a working default: the page renders something useful on first load,
  never an empty frame waiting for input

## Gen AI / streaming patterns

- For streaming API responses: use requests with stream=True + st.write_stream
- Show a placeholder while waiting — never a blank area
- Label AI-generated content clearly in the UI

## Code output per task — in this order

1. File structure (only files for this task)
2. api_client.py additions (typed functions for new endpoints)
3. Page or component Python file
4. Session state schema (what keys are stored and why)
5. Smoke test (can the page render without errors given mock API responses)
6. Config additions (secrets.toml keys or env vars)

## Quality rules

- No API calls inline in UI code — always via api_client module
- All API calls wrapped in try/except with st.error() display
- No hardcoded URLs or ports — all from config
- Session state keys defined as constants, not magic strings
- **No secrets in the app.** Streamlit runs the whole script server-side, but anything in a
  chart, a caption or an error message is on screen — surface the failure, not the stack trace
- Remember the script re-runs top to bottom on **every** interaction: no unguarded write, no
  API call outside a cached function or an explicit button, no counter incremented at module level
- Cache keys must cover every input a cached function reads, or it will serve another user's
  filter results

## Acceptance criteria check

Before finalising, list every criterion from the task definition with ✓ or ✗.
