---
name: chainlit
kind: guideline
description: >
  Standards for Chainlit conversational apps: component conventions, conversation flow, and
  quality rules. Applies when building or changing a Chainlit app.
applies_to:
  - "**/chainlit.md"
  - "**/.chainlit/**"
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
- **Read the launch context on chat start** — URL parameters when embedded as a panel — and
  treat every one of them as untrusted input: validate, and degrade gracefully when absent
- Streaming: use cl.Message.stream_token() for token-by-token display
- Context injection: pre-seed the conversation on mount when launch context is present, so the
  user arrives at an answer rather than an empty box

## Conversation flow standards

- On start: read and validate launch context → call the context endpoint → pre-seed the first
  message
- On message: classify intent (follow-up vs new question) → select the prompt template **by
  key** from the prompt files; never build the prompt inline
- Multi-turn: pass the last N turns as conversation history, N from config
- Fallback: if an API call fails, show a friendly error and offer to retry
- Never leave the user with a blank area or a spinner without explanation
- Every streamed response is cancellable, and a cancelled turn leaves the history consistent
- Attribute the answer: show which sources or tools produced it, and say so when there were none

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
- Launch context validated on start — missing values handled gracefully
- Conversation history capped (default: last 10 turns) to control token usage — cap from config
- No hardcoded API URLs — from environment variables
- **No prompt text in `app.py`.** System prompts and templates load from prompt files by key
- The guardrail layer is the conversational API's, not the UI's — this app must not be the only
  thing standing between user input and a model
- Never render model output as raw HTML; never echo an upstream stack trace to the user

## Acceptance criteria check

Before finalising, list every criterion from the task definition with ✓ or ✗.
