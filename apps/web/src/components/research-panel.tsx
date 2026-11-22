"use client";
import { useEffect, useRef, useState, type FormEvent } from "react";
import {
  BookOpen,
  Check,
  FlaskConical,
  KeyRound,
  LoaderCircle,
  Play,
  Search,
  ShieldCheck,
  Square,
  X,
} from "lucide-react";
import {
  api,
  type AIConnection,
  type Brief,
  type Project,
  type ResearchRun,
  type Evidence,
  type Competitor,
} from "../lib/api";

const BUSY = new Set(["planning", "researching", "synthesizing", "reviewing"]);
const LABELS: Record<string, string> = {
  planner: "Research planner",
  market_search: "Market researcher · search",
  market_sources: "Market researcher · source collection",
  market_analysis: "Market researcher · analysis",
  competitor_search: "Competitor analyst · search",
  competitor_sources: "Competitor analyst · source collection",
  competitor_analysis: "Competitor analyst · comparison",
  customer_analysis: "Customer research analyst",
  synthesizer: "Insight synthesizer",
  reviewer: "Evidence reviewer",
};
function statusLabel(value: string) {
  return value.replaceAll("_", " ");
}

export function ResearchPanel({
  project,
  onBrief,
  onError,
}: {
  project: Project;
  onBrief: (b: Brief | null) => void;
  onError: (e: unknown) => void;
}) {
  const [connection, setConnection] = useState<AIConnection | null>(null);
  const [connecting, setConnecting] = useState(false);
  const [history, setHistory] = useState<ResearchRun[]>([]);
  const [selected, setSelected] = useState("");
  const [run, setRun] = useState<ResearchRun | null>(null);
  const [busy, setBusy] = useState(false);
  const [ready, setReady] = useState(false);
  const [localError, setLocalError] = useState("");
  const [refresh, setRefresh] = useState(0);
  const onBriefRef = useRef(onBrief);
  const onErrorRef = useRef(onError);
  onBriefRef.current = onBrief;
  onErrorRef.current = onError;

  useEffect(() => {
    let alive = true;
    Promise.all([
      api<AIConnection>("/settings/ai"),
      api<ResearchRun[]>(`/projects/${project.id}/runs`),
    ])
      .then(([settings, runs]) => {
        if (!alive) return;
        setConnection(settings);
        setHistory(runs);
        if (runs[0]) setSelected(runs[0].id);
      })
      .catch((e) => {
        if (alive) onErrorRef.current(e);
      })
      .finally(() => {
        if (alive) setReady(true);
      });
    return () => {
      alive = false;
    };
  }, [project.id]);

  useEffect(() => {
    if (!selected) return;
    let alive = true;
    let timer: ReturnType<typeof setTimeout>;
    async function poll() {
      try {
        const value = await api<ResearchRun>(`/runs/${selected}`);
        if (!alive) return;
        setRun(value);
        onBriefRef.current(value.brief || null);
        setHistory((old) => {
          const exists = old.some((r) => r.id === value.id);
          return exists
            ? old.map((r) => (r.id === value.id ? value : r))
            : [value, ...old];
        });
        if (BUSY.has(value.status)) timer = setTimeout(poll, 2000);
      } catch (e) {
        if (alive) {
          setLocalError(
            e instanceof Error ? e.message : "Could not refresh the run.",
          );
          onErrorRef.current(e);
        }
      }
    }
    void poll();
    return () => {
      alive = false;
      clearTimeout(timer);
    };
  }, [selected, refresh]);

  async function start(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setLocalError("");
    const form = new FormData(event.currentTarget);
    try {
      const value = await api<ResearchRun>(`/projects/${project.id}/runs`, {
        competitors: String(form.get("competitors") || "")
          .split("\n")
          .map((s) => s.trim())
          .filter(Boolean),
        customer_notes: String(form.get("customer_notes") || ""),
      });
      onBriefRef.current(null);
      setRun(value);
      setSelected(value.id);
      setRefresh((n) => n + 1);
    } catch (e) {
      setLocalError(
        e instanceof Error ? e.message : "Could not start research.",
      );
      onErrorRef.current(e);
    } finally {
      setBusy(false);
    }
  }
  async function action(action: string) {
    if (!run) return;
    setBusy(true);
    setLocalError("");
    try {
      const value = await api<ResearchRun>(`/runs/${run.id}/${action}`, {});
      setRun(value);
      setRefresh((n) => n + 1);
    } catch (e) {
      setLocalError(
        e instanceof Error ? e.message : "Could not update the run.",
      );
      onErrorRef.current(e);
    } finally {
      setBusy(false);
    }
  }
  const activeRun =
    history.find(
      (r) => BUSY.has(r.status) || r.status === "awaiting_approval",
    ) ||
    (run && (BUSY.has(run.status) || run.status === "awaiting_approval")
      ? run
      : null);
  return (
    <section className="research-panel" aria-label="Research workflow">
      <div className="research-toolbar">
        <div>
          <span className="research-kicker">YOUR PM RESEARCH TEAM</span>
          <h2>Turn your question into evidence.</h2>
        </div>
        <button
          className="button secondary"
          onClick={() => setConnecting(true)}
        >
          <KeyRound size={17} />
          {connection?.configured ? "AI connected" : "Connect AI"}
        </button>
      </div>
      <p className="research-description">
        A planner defines the work. Market and competitor agents investigate in
        parallel. A synthesizer connects the findings, and a reviewer checks
        their evidence.
      </p>
      {!ready && <p role="status">Loading research workspace…</p>}
      {ready && !connection?.configured && (
        <div className="connection-notice">
          <KeyRound size={20} />
          <div>
            <strong>Connect AI to start live research</strong>
            <p>
              Add an OpenAI API key using “Connect AI”. No live run has started.
              Your key stays on this local server and is never returned to the
              browser.
            </p>
          </div>
        </div>
      )}
      <form className="research-inputs" onSubmit={start}>
        <div className="form-row">
          <label>
            Competitors to investigate{" "}
            <span>optional · up to 5, one per line</span>
            <textarea
              name="competitors"
              rows={3}
              maxLength={2500}
              placeholder={
                "e.g. Zoho Invoice\nhttps://www.freshbooks.com/pricing"
              }
            />
          </label>
          <label>
            Customer research notes{" "}
            <span>optional · 15,000 characters maximum</span>
            <textarea
              name="customer_notes"
              rows={3}
              maxLength={15000}
              placeholder="Paste interview notes or feedback. These go to the AI analyst, not to web search."
            />
          </label>
        </div>
        <div className="research-start">
          <p>
            Your question, audience and competitor names are sent to OpenAI for
            research. Customer notes are analyzed privately by the model and
            excluded from web-search inputs. API usage is billed to your API
            project.
          </p>
          <button
            className="button primary"
            disabled={
              !ready || busy || !connection?.configured || Boolean(activeRun)
            }
          >
            <Play size={17} />
            {busy ? "Starting…" : "Create research plan"}
          </button>
        </div>
        <p className="run-limits">
          Per run: up to 12 AI requests, 4 web-tool calls and 8 downloaded
          pages. Research waits for your plan approval. Limits also apply across
          resumes.
        </p>
      </form>
      {localError && (
        <p role="alert" className="error">
          {localError}
        </p>
      )}
      {history.length > 0 && (
        <label className="run-history">
          Research history
          <select
            aria-label="Research history"
            value={selected}
            onChange={(e) => {
              onBriefRef.current(null);
              setRun(null);
              setLocalError("");
              setSelected(e.target.value);
            }}
          >
            {history.map((r) => (
              <option value={r.id} key={r.id}>
                {new Date(r.created_at * 1000).toLocaleString()} ·{" "}
                {statusLabel(r.status)}
              </option>
            ))}
          </select>
        </label>
      )}
      {run && (
        <div className="run-card" aria-live="polite">
          <div className="run-card-heading">
            <span className={`run-status status-${run.status}`}>
              {BUSY.has(run.status) ? (
                <LoaderCircle size={17} className="spinning" />
              ) : (
                <Check size={17} />
              )}{" "}
              {statusLabel(run.status)}
            </span>
            <span>
              {run.model} · {run.usage.model_requests}/{run.usage.max_requests}{" "}
              AI requests
            </span>
          </div>
          {run.error && (
            <p role="alert" className="error">
              {run.error}
            </p>
          )}
          {Boolean(run.cancel_requested) && BUSY.has(run.status) && (
            <p>
              Cancellation requested. An in-flight provider call may finish and
              be billed; no further calls will be started.
            </p>
          )}
          {run.plan && (
            <details
              open={run.status === "awaiting_approval"}
              className="plan-details"
            >
              <summary>Research plan</summary>
              <h3>{run.plan.objective}</h3>
              <ul>
                {run.plan.questions.map((q, i) => (
                  <li key={i}>{q}</li>
                ))}
              </ul>
              <div className="plan-columns">
                <div>
                  <h4>Market research</h4>
                  <ul>
                    {run.plan.market_queries.map((q, i) => (
                      <li key={i}>{q}</li>
                    ))}
                  </ul>
                </div>
                <div>
                  <h4>Competitor analysis</h4>
                  <ul>
                    {run.plan.competitor_queries.map((q, i) => (
                      <li key={i}>{q}</li>
                    ))}
                  </ul>
                </div>
              </div>
              <h4>Completion criteria</h4>
              <ul>
                {run.plan.completion_criteria.map((q, i) => (
                  <li key={i}>{q}</li>
                ))}
              </ul>
              {run.plan.assumptions.length > 0 && (
                <>
                  <h4>Assumptions to check</h4>
                  <ul>
                    {run.plan.assumptions.map((q, i) => (
                      <li key={i}>{q}</li>
                    ))}
                  </ul>
                </>
              )}
            </details>
          )}
          {run.status === "awaiting_approval" && (
            <div className="run-actions">
              <button
                className="button primary"
                disabled={busy || !connection?.configured}
                onClick={() => void action("approve")}
              >
                <Search size={17} /> Approve plan and research
              </button>
              <span>
                You can cancel and start a new run to change the inputs.
              </span>
            </div>
          )}
          <ol className="agent-timeline">
            {run.stages.map((s) => (
              <li key={s.name}>
                <span className={`agent-status ${s.status}`}>
                  {s.status === "running" ? (
                    <LoaderCircle className="spinning" size={16} />
                  ) : s.status === "completed" ? (
                    <Check size={16} />
                  ) : (
                    <Square size={14} />
                  )}
                </span>
                <div>
                  <strong>{LABELS[s.name] || s.name}</strong>
                  <span>{statusLabel(s.status)}</span>
                  {s.error && <p>{s.error}</p>}
                </div>
              </li>
            ))}
          </ol>
          {run.status === "partial" && (
            <div className="connection-notice">
              <ShieldCheck size={19} />
              <p>
                This brief has coverage gaps or removed claims. Inspect its
                limitations before using it.
              </p>
            </div>
          )}
          <div className="run-actions">
            {(BUSY.has(run.status) || run.status === "awaiting_approval") && (
              <button
                className="button secondary"
                disabled={busy || Boolean(run.cancel_requested)}
                onClick={() => void action("cancel")}
              >
                <Square size={15} /> Cancel run
              </button>
            )}
            {["failed", "interrupted"].includes(run.status) && (
              <button
                className="button secondary"
                disabled={busy || !connection?.configured}
                onClick={() => void action("resume")}
              >
                Resume saved run
              </button>
            )}
            <button
              className="button secondary"
              disabled={busy}
              onClick={() => setRefresh((n) => n + 1)}
            >
              Refresh status
            </button>
            <span>
              {run.usage.input_tokens.toLocaleString()} input /{" "}
              {run.usage.output_tokens.toLocaleString()} output tokens.{" "}
              {run.usage.unknown_requests > 0
                ? "Some request usage is unknown. "
                : ""}
              Dollar cost is available in provider billing.
            </span>
          </div>
        </div>
      )}
      {!run && ready && (
        <div className="research-empty">
          <BookOpen size={24} />
          <div>
            <h3>No research brief yet.</h3>
            <p>
              Create a plan for “{project.question}” to begin. A sample is
              available only when you explicitly open it.
            </p>
            <button
              className="text-button"
              onClick={async () => {
                try {
                  onBriefRef.current(
                    await api<Brief>(`/projects/${project.id}/sample-brief`),
                  );
                } catch (e) {
                  onErrorRef.current(e);
                }
              }}
            >
              <FlaskConical size={16} /> View synthetic example
            </button>
          </div>
        </div>
      )}
      {connecting && (
        <ConnectionDialog
          value={connection}
          onClose={() => setConnecting(false)}
          onConnected={(value) => {
            setConnection(value);
            setConnecting(false);
          }}
        />
      )}
    </section>
  );
}

function ConnectionDialog({
  value,
  onClose,
  onConnected,
}: {
  value: AIConnection | null;
  onClose: () => void;
  onConnected: (v: AIConnection) => void;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    ref.current?.showModal();
  }, []);
  async function connect(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = e.currentTarget;
    const fields = new FormData(form);
    setBusy(true);
    setError("");
    try {
      const result = await api<AIConnection>("/settings/ai", {
        api_key: fields.get("api_key"),
        model: fields.get("model"),
      });
      form.reset();
      onConnected(result);
    } catch (error) {
      setError(error instanceof Error ? error.message : "Could not connect.");
    } finally {
      setBusy(false);
    }
  }
  return (
    <dialog
      ref={ref}
      className="create-dialog ai-dialog"
      aria-label="Connect AI"
      onCancel={onClose}
    >
      <div className="dialog-heading">
        <KeyRound size={26} />
        <button
          className="icon-button"
          aria-label="Close AI settings"
          onClick={onClose}
        >
          <X size={22} />
        </button>
      </div>
      <h2>Connect your research team</h2>
      <p>
        Use an OpenAI API project with model and web-search access. A ChatGPT
        password is not an API key.
      </p>
      <form onSubmit={connect}>
        <label>
          OpenAI API key
          <input
            name="api_key"
            type="password"
            autoComplete="off"
            required
            minLength={20}
            maxLength={512}
            placeholder="Paste your API key here"
          />
        </label>
        <label>
          Model
          <input
            name="model"
            required
            defaultValue={value?.model || "gpt-5-mini"}
            pattern="[a-zA-Z0-9_.:\-]{1,100}"
          />
        </label>
        <p className="key-help">
          The key is sent only to this local server and OpenAI. It stays in
          server memory for your account, is not written to the database or
          browser storage, and is cleared when the server restarts. Connecting
          checks model access; research uses paid API requests.
        </p>
        <a
          href="https://platform.openai.com/api-keys"
          target="_blank"
          rel="noopener noreferrer"
        >
          Manage OpenAI API keys
        </a>
        {error && (
          <p role="alert" className="error">
            {error}
          </p>
        )}
        <button className="button primary full" disabled={busy}>
          {busy ? "Checking connection…" : "Connect AI"}
        </button>
      </form>
      {value?.configured && (
        <button
          className="text-button disconnect"
          disabled={busy}
          onClick={async () => {
            setBusy(true);
            try {
              onConnected(
                await api<AIConnection>("/settings/ai/disconnect", {}),
              );
            } catch (e) {
              setError(
                e instanceof Error ? e.message : "Could not disconnect.",
              );
            } finally {
              setBusy(false);
            }
          }}
        >
          Disconnect session key
        </button>
      )}
    </dialog>
  );
}

export function CompetitorTable({
  competitors,
  evidence,
  onEvidence,
}: {
  competitors: Competitor[];
  evidence: Evidence[];
  onEvidence: (e: Evidence) => void;
}) {
  return (
    <section className="competitor-section">
      <h3>Competitor comparison</h3>
      <p>
        Only source-supported attributes that passed evidence review are shown.
        “Not established” means this run did not establish the attribute.
      </p>
      <div className="table-scroll">
        <table>
          <thead>
            <tr>
              <th>Competitor</th>
              <th>Positioning</th>
              <th>Features</th>
              <th>Pricing</th>
              <th>Gaps</th>
            </tr>
          </thead>
          <tbody>
            {competitors.map((c, i) => (
              <tr key={`${c.name}-${i}`}>
                <th scope="row">{c.name}</th>
                {["positioning", "features", "pricing", "gaps"].map((d) => (
                  <td key={d}>
                    {c.facts.filter((f) => f.dimension === d).length ? (
                      c.facts
                        .filter((f) => f.dimension === d)
                        .map((f) => (
                          <p key={f.id}>
                            {f.text}{" "}
                            {f.evidence_ids.map((id) => {
                              const source = evidence.find((e) => e.id === id);
                              return source ? (
                                <button
                                  key={id}
                                  className="citation"
                                  aria-label={`View competitor evidence ${id}`}
                                  onClick={() => onEvidence(source)}
                                >
                                  {evidence.indexOf(source) + 1}
                                </button>
                              ) : null;
                            })}
                          </p>
                        ))
                    ) : (
                      <span className="unknown">Not established</span>
                    )}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
