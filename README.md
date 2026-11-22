# Fieldnotes — PM research workspace

**Live website: [Open Fieldnotes](https://fieldnotes-pm-workspace.bizverto-tech.chatgpt.site)**

Fieldnotes is already deployed; no hosting setup or local installation is needed to use it. Sign in with ChatGPT on the live website. See the [current application README](../fieldnotes-public/README.md) for its features and usage instructions.

This directory contains the earlier local prototype. The setup, local accounts and implementation details below apply only to that prototype, not the live website.

Fieldnotes coordinates a research planner, market researcher, competitor analyst, optional customer-notes analyst, synthesizer and evidence reviewer. The live workflow uses the saved project question; the old invoice example is available only through an explicit **View synthetic example** button.

## Start locally

Requirements: Node.js 20.17+ and Python 3.12. From this repository in PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r apps/backend/requirements.lock.txt
npm ci
npm run dev
```

Dependencies are already installed in the implementation workspace. `npm run dev` applies migrations and starts FastAPI on 127.0.0.1:8000 and Next.js on 127.0.0.1:3000. Open http://127.0.0.1:3000. Ctrl+C stops the app. Ports 3000 and 8000 must be free. On macOS/Linux use `python3` and `.venv/bin/python` during setup.

Accounts, projects and research data persist in ignored `data/fieldnotes.db`. Existing milestone-01 accounts and projects are preserved by migration 002. Accounts are local to this app: create an account first, then sign in with the same details. ChatGPT login details do not sign you in here. Local passwords require at least 12 characters.

## Run your research team

1. Sign in and create or open a project with a specific research question, audience and geography.
2. Choose **Connect AI**. Enter an OpenAI API key and an accessible model supporting Responses, structured outputs and web search. The configurable default is `gpt-5-mini`.
3. Optionally supply up to five competitor names or public URLs, and first-party customer research notes.
4. Choose **Create research plan**. The planner makes an API request and saves its proposed questions, queries, assumptions and completion criteria.
5. Review the plan, then choose **Approve plan and research**. Market and competitor branches investigate concurrently. Supplied customer notes are analyzed in a third branch.
6. Watch persisted agent progress. The synthesizer builds a question-specific brief; an independent AI reviewer evaluates every published report block and comparison fact.
7. Inspect evidence drawers and original source links, read the limitations and export the brief as Markdown.

Research uses paid API requests billed to your API project. The connection dialog checks key/model access; a complete web-search run also requires that capability to be enabled for the project. No AI key is bundled and there is no fake/live fallback.

### Connection and privacy

Keys entered in Connect AI are held in backend memory for your local account, never written to the database, returned by API responses or stored in localStorage. Reconnect after restarting the server. **Disconnect session key** removes that in-memory override; it does not remove a server-wide environment connection.

Alternatively put `OPENAI_API_KEY` and optionally `OPENAI_MODEL` in the ignored root `.env`. The backend loads this file at startup. A server-wide key is intentionally available to all accounts on that local server; prefer per-account Connect AI when sharing the instance. No key should be pasted into this chat or committed.

The question, audience, geography, competitor names and generated queries go to OpenAI web research. Optional customer notes go to the model for private analysis and synthesis; they are excluded from the planner/search context and queries generated from that context. Notes, source snapshots and outputs are retained in the local database. The application has no cross-project retrieval. Do not deploy this prototype publicly without reviewing authentication, retention and provider data handling.

### What the report guarantees—and does not

- A published excerpt must match normalized text in a saved source snapshot. Public-page quotations are capped at 25 words per page across admitted evidence; excess excerpts are omitted with a limitation.
- Published factual observations and inferences require valid evidence references and an affirmative AI reviewer decision. Unreviewed or rejected claims are withheld.
- Each published competitor fact has its own excerpt and review decision. Unestablished positioning, features, pricing or gaps remain **Not established**. An absent feature mention is not evidence of a product gap.
- Recommendations and validation experiments are explicitly typed as untested hypotheses/experiments.
- Source failures, rejected claims, missing customer research and incomplete coverage remain visible. A partial brief can still be useful, but is not a completed or representative study.
- The reviewer is an AI model, not a human. Exact quotation matching and AI agreement cannot establish source truth, population prevalence, completeness or market demand.

## Local execution model

This milestone runs bounded background thread pools inside one FastAPI process, with SQL checkpoints in SQLite or PostgreSQL. It does not require Redis/Celery. Do not run multiple API workers or replicas with this local runner.

The planner stops at approval. The research branches are independently checkpointed; completed stages are reused on explicit resume. A server restart marks in-flight runs **interrupted** and in-flight provider usage **unknown**. It never automatically repeats an ambiguous paid request. Reconnect the same model and resume a failed/interrupted run. Cancelled and completed runs are immutable; start a new run to change inputs or retry a partial result.

Limits per run, including resumes: 12 model requests, up to 4 web-tool calls, up to 8 downloaded public pages. Each provider response is capped at 10,000 output tokens (5,000 for discovery). These are request/token limits, not a fixed dollar budget. Token usage is recorded; dollar cost is not guessed and remains available in provider billing. Cancellation prevents new calls and publication; an in-flight request may finish and be billed.

The fetcher accepts public HTTP(S) pages on standard ports, rejects private/local/mixed DNS destinations, pins connections to validated addresses while preserving TLS hostname verification, rechecks redirects, and bounds page size and text length. HTML/text extraction is supported. PDFs, login-gated pages, browser-only pages and large pages can become coverage gaps rather than being bypassed.

## Repository

```text
apps/web/src/components/research-panel.tsx   Run controls, approval, history, comparison
apps/backend/app/research/routes.py         Authorized run and connection APIs
apps/backend/app/research/workflow.py       Roles, parallel branches, checkpoints, review gate
apps/backend/app/research/provider.py       OpenAI transport, metering, key isolation
apps/backend/app/research/web.py            Public-source extraction and network restrictions
apps/backend/app/research/schemas.py        Structured agent contracts
apps/backend/migrations/                   Versioned schema upgrades
apps/backend/tests/                        API, workflow and provider-contract tests
contracts/openapi.json                     Exported API schema
```

Authentication in this local prototype remains the salted-password/HttpOnly-session implementation from milestone 01, with per-project ownership checks. Its file uploads, full report editing, collaborative work, scheduled monitoring and distributed workers remain unimplemented here. The public application is already deployed separately at the live URL above.

## Checks

```powershell
$env:PYTHONPATH='apps/backend'
.\.venv\Scripts\python.exe -m pytest apps/backend/tests -q
npm run typecheck
npm run build
npm audit
```

Backend workflow tests use explicit offline provider doubles and temporary databases. They do not validate live model quality. See `docs/verification.md` for what was actually exercised. The browser regression journey is included; after starting the app, you can install Playwright Chromium and run `npm run test:e2e` on your own machine.

## Optional Docker/PostgreSQL runtime

Start Docker Desktop and stop the native runtime first:

```powershell
Copy-Item .env.example .env
# Set a URL-safe POSTGRES_PASSWORD in .env; optionally set OPENAI_API_KEY.
docker compose up --build
```

Open http://127.0.0.1:3000. The web port is loopback-only, and API/database ports are not published. PostgreSQL data is a separate volume from native SQLite. Compose passes optional model/key environment configuration to the API. The Redis `future-workers` profile is reserved for later distributed execution. Container execution remains unverified on this machine because the Docker engine is stopped.
