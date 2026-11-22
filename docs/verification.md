# Research-engine verification

Verified on November 19, 2026, on Windows with Python 3.12 and Node.js 20.17.

## Checks actually completed

- 33 backend tests passed. They cover the original account/session/project protections and the new research workflow: missing-key gating, explicit plan approval, genuinely concurrent research branches (using a barrier), question-specific synthesis, customer-note exclusion from search, reviewer filtering, exact-quote rejection, usage accounting, cancellation before publication, saved-stage reuse, interrupted-call recovery, duplicate active-run prevention, per-account key isolation, source-network restrictions the structured Responses request contract, complete source failure, all-claims reviewer rejection, and partial competitor coverage.
- Workflow tests use explicit offline provider doubles and temporary databases. They test orchestration and gates, not model accuracy or live provider compatibility.
- The real bounded public-page fetcher successfully downloaded and extracted the Python documentation over HTTPS using a pinned public address with the original TLS hostname. A much larger documentation page hit the size limit and was rejected, as intended.
- The Next.js production build and application TypeScript checks passed.
- Migration 002 applied to the existing local database without replacing accounts or projects.
- The restarted native runtime returned the updated health response through the frontend proxy.
- In-app browser checks confirmed the new project research controls, missing-key message, disabled research action before connection, private key setup dialog, and explicitly opt-in synthetic example. Reload returned to the live research workspace instead of silently showing the example.
- The Playwright regression journey was updated and type-checked, but the Playwright runner was not executed in this session.

## Verification limits

No OpenAI API key was available. No actual paid planner, web-search or multi-agent model run was executed. End-to-end live model behavior, model access, research quality and live token/cost totals remain unverified until a user connects an API project and runs research. The app exposes that requirement and does not simulate a live success or populate user history with a fabricated research run.

Docker Compose configuration is validated, but container/PostgreSQL execution remains unverified because the Docker engine is stopped. Authentication remains local-development auth. The background runner supports one API process; it is not a distributed production worker system.

The native app was restarted for the user to access the new controls. Connect AI accepts a per-account in-memory key; no credentials were added to source control or local reports during implementation. A screenshot of the empty connection dialog is saved alongside the project output.

The test stack emits a non-failing upstream httpx/TestClient deprecation warning.
