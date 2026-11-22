# Research engine architecture

## Roles and tools

The Python runner executes these model roles with separate instructions and structured output schemas:

1. Planner: project context -> research questions, search queries, assumptions and coverage criteria. It cannot browse and never receives customer-note content.
2. Market researcher: OpenAI web-search discovery -> bounded downloaded source snapshots -> structured finding extraction.
3. Competitor analyst: independent web discovery and extraction -> comparison facts with an exact quotation per attribute.
4. Optional customer-notes analyst: supplied first-party notes only; no search tools.
5. Synthesizer: verified evidence and findings -> typed claims, opportunity hypotheses and validation experiments.
6. Reviewer: fresh context with plan, draft, comparator facts and evidence -> one support decision per claim/fact and coverage gaps. It cannot add claims.

Market and competitor work share a bounded branch executor and actually run concurrently. The customer branch joins them when notes are present. Application code, not the planner, controls tool access, scheduling, cancellation and limits. The final renderer introduces no new model-generated prose.

## Persistence

`research_runs` records an input snapshot, status, model, approved plan and final brief. The nullable unique `active_project_id` prevents two active runs for the same project. `agent_stages` has a unique run/name key and stores completed outputs for explicit resume. `research_sources` stores normalized text, original URL, hash and retrieval time. `model_calls` stores per-call status and usage without credentials or request bodies.

The connection vault is process-local and keyed by authenticated user ID. Optional environment configuration is server-wide. Keys never enter persisted stage inputs, run config, source snapshots or API results. The prototype requires a single API process: scale-out requires a durable queue, distributed ownership/leases and an appropriately protected secret store.

## Publication gate

Downloaded snapshots are the evidence authority, not search summaries. Exact quotations are checked against normalized snapshot text before synthesis. Public-source quotation totals are capped at 25 words per URL. Each report block has a code-assigned ID; comparison facts occupy a separate ID namespace. Only explicit reviewer approvals with valid evidence references survive publication. Hypotheses and experiments remain explicitly untested. Failed quote matches, rejected claims and missing report sections produce coverage limitations and partial status where appropriate.

Evidence correctness is not source truth. The reviewer is another AI invocation and can be wrong; reports clearly disclose that no human review has occurred. First-party notes preserve sample limitations; web evidence does not validate demand. Snapshot character locations refer to extracted text, not original HTML line numbers.

## Interruptions and spend

A stage commits its result before downstream execution. Startup marks in-flight work interrupted; there is no automatic paid retry. Explicit resume reuses successful stages and retries only unfinished/failed stages. Provider calls that may have been accepted before connection loss or process termination are recorded as unknown. Exactly-once billing is not guaranteed.

Cancellation is checked before calls, source downloads, stage commits and publication. The final database update is conditional on the cancellation flag. In-flight external work cannot reliably be recalled. Requests and tool calls are bounded; monetary cost is not inferred from token counts.

## Existing workspace

Next.js proxies same-origin API requests to FastAPI. Existing account/session/project authorization is preserved. Live run history is the default project view. The synthetic invoice fixture now has a separate explicit endpoint and opt-in UI; no missing key, source failure or failed model call falls back to it. Completed/partial briefs are stored independently of that fixture.
