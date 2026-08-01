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
- Requests or httpx for FastAPI calls
- Streamlit session_state for UI state management
- Streamlit components for iframe embedding (Chainlit panel)

## Component standards

- One Python file per page or major feature area
- All API calls in a dedicated api_client.py module — never inline in UI code
- Use st.cache_data for data that changes per pipeline run (TTL = 60s)
- Use st.cache_resource for connections and clients (app lifetime)
- Every API call has a spinner, error message, and empty state
- Config (API base URL, ports) from environment variables or secrets.toml

## Layout standards

- st.set_page_config called once at the top of the entry file
- Sidebar for filters (line selector, date range, severity filter)
- Main area: tabs for Dashboard / SHAP / Compliance
- Chainlit panel: st.components.v1.iframe embedded on the right side
- Use st.columns for side-by-side layout — avoid nested expanders

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

## Acceptance criteria check

Before finalising, list every criterion from the task definition with ✓ or ✗.
