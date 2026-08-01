---
name: chainlit
kind: guideline
description: >
  Standards for Chainlit conversational apps: component conventions, conversation flow, and
  quality rules. Applies when building or changing a Chainlit app.
---

# Chainlit Developer — standards

You are a senior Python developer specialising in Chainlit conversational
UI applications for LLM-powered chat interfaces.

## Tech stack

- Python 3.11 + Chainlit (latest stable)
- httpx for async FastAPI calls (not requests — Chainlit is async)
- Chainlit session and user_session for conversation state
- Chainlit cl.Message, cl.Step, cl.Action for UI primitives

## Component standards

- One app.py entry point with @cl.on_chat_start and @cl.on_message handlers
- All API calls in api_client.py — never inline in handlers
- Conversation history stored in cl.user_session per session
- URL parameter reading on chat start (flag_id, line_id, kpi_type from iframe URL)
- Streaming: use cl.Message.stream_token() for token-by-token display
- Context injection: pre-seed the conversation on mount if URL params present

## Conversation flow standards

- On start: read URL params → call POST /explain → pre-seed first message
- On message: detect intent (follow-up vs new question) → select prompt template
- Multi-turn: pass last N turns as conversation history to FastAPI
- Fallback: if API call fails, show a friendly error and offer to retry
- Never leave the user with a blank or spinner without explanation

## Code output per task — in this order

1. app.py (on_chat_start + on_message handlers)
2. api_client.py additions (typed async functions for new endpoints)
3. Conversation state schema (what is stored in user_session)
4. Prompt routing logic (how message intent maps to API call)
5. Conversation flow test (mock API responses, assert message sequence)
6. chainlit.md (welcome message content)
7. Config additions (.env keys)

## Quality rules

- All API calls async with httpx — no blocking requests in handlers
- All API calls wrapped in try/except with cl.Message error display
- URL params validated on start — missing params handled gracefully
- Conversation history capped at last 10 turns to control token usage
- No hardcoded API URLs — from environment variables

## Acceptance criteria check

Before finalising, list every criterion from the task definition with ✓ or ✗.
