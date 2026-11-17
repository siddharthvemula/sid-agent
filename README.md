# SidAgent

A personal AI agent tailored to Sid Vemula — built to **do** things, not just answer questions.

**Stage 2 (current):** full stack — agent engine, real LLM adapters, FastAPI backend, React chat UI. Still runs with *no API keys and no cost* on the mock provider; add a key to go live:

- **Public-layer profile** (`sid_agent/data/profile.json`) — school, degree, courses, projects, experience, skills, goals. No private context, by design; a test guards the boundary.
- **SQLite store** — tasks, internship applications, and key-value memories.
- **Action tools** — create/list/complete tasks, log/list/update applications, remember/recall facts, and a *live* UMD course/prerequisite lookup via the public umd.io API.
- **Provider-flexible LLM interface** — plan → execute → compose. A deterministic mock provider runs everything with no key; Claude (Anthropic Messages API) and OpenAI (function calling) adapters are implemented over raw HTTPS with an injectable transport, so they're unit-tested without a key and need no vendor SDK.
- **Fact-lock rule** — the agent only reports what a tool returned. If nothing matches, it says so instead of improvising.

## Run it

```bash
cd sid-agent
python -m unittest discover tests        # core test suite (stdlib only)

# CLI
python -m sid_agent.cli "remind me to submit the form by 2026-11-20"
python -m sid_agent.cli "log application to Acme for SWE Intern"
python -m sid_agent.cli                  # interactive mode

# Web stack (Stage 2)
python -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python -m unittest discover tests   # full suite incl. API + providers (21 tests)
.venv/bin/uvicorn sid_agent.api:app --port 8000
cd frontend && npm install && npm run dev     # UI on http://localhost:5173
```

Go live with a real model (optional): set `ANTHROPIC_API_KEY` (or
`OPENAI_API_KEY`) and `SID_AGENT_PROVIDER=claude` (or `openai`) before
starting the API or CLI. The core engine stays zero-dependency — Python
3.10+ standard library only; FastAPI is used solely for the web layer.

## Design decisions worth talking about

1. **Doing over answering** — tools first; chat is just the interface to them.
2. **Layered data with a privacy guard** — personal data is separated into layers; v1 ships the public layer only, and `tests/test_profile.py` fails the build if private material leaks into it.
3. **Provider abstraction** — the agent loop never talks to a vendor SDK directly, so models can be swapped without touching tools or the store.
4. **Approval rule** — the agent drafts and prepares; it never sends, submits, or deletes without explicit approval.
5. **Evals from day one** — `evals/eval_questions.json` seeds a set of requests with expected tool/store outcomes (grows to ~30 in Stage 3).

## Roadmap

- **Stage 1 (done):** engine, tools, store, mock provider, CLI, tests, eval seed.
- **Stage 2 (done):** Claude + OpenAI adapters (unit-tested via fake transport; live use needs an API key), FastAPI backend (`/chat`, `/tasks`, `/applications`, `/profile`, `/tools`), React + TypeScript chat UI with live task/application sidebar.
- **Stage 3:** full eval runner incl. multi-step tasks, demo script, deployment.
- **Later (only on Sid's say-so):** private data layer, calendar/email connectors, proactive reminders.
