"use client";

import { useEffect, useRef, useState, type FormEvent } from "react";
import {
  ArrowDownToLine,
  ArrowRight,
  ArrowUpRight,
  BookOpen,
  Check,
  ChevronRight,
  FileText,
  FlaskConical,
  Folder,
  Leaf,
  LogOut,
  Plus,
  Search,
  ShieldCheck,
  Sparkles,
  X,
} from "lucide-react";
import {
  api,
  ApiError,
  type Brief,
  type Evidence,
  type Project,
  type User,
} from "../lib/api";

import { ResearchPanel, CompetitorTable } from "../components/research-panel";

function Mark() {
  return (
    <span className="brand">
      <span className="brand-icon">
        <Leaf size={21} />
      </span>
      fieldnotes<span className="brand-dot">.</span>
    </span>
  );
}

export default function Home() {
  const [user, setUser] = useState<User | null>(null);
  const [ready, setReady] = useState(false);
  const [projects, setProjects] = useState<Project[]>([]);
  const [active, setActive] = useState<Project | null>(null);
  const [brief, setBrief] = useState<Brief | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [creating, setCreating] = useState(false);
  const [evidence, setEvidence] = useState<Evidence | null>(null);
  const [filter, setFilter] = useState("");
  const createDialog = useRef<HTMLDialogElement>(null);
  const evidenceDialog = useRef<HTMLDialogElement>(null);
  const requestVersion = useRef(0);

  function failure(e: unknown) {
    if (e instanceof ApiError && e.status === 401) {
      setUser(null);
      setActive(null);
      setBrief(null);
      setProjects([]);
      setCreating(false);
      setEvidence(null);
    }
    setError(
      e instanceof Error ? e.message : "Something went wrong. Please retry.",
    );
  }
  async function openProject(project: Project, updateUrl = true) {
    const version = ++requestVersion.current;
    setActive(project);
    setBrief(null);
    setLoading(true);
    setError("");
    if (updateUrl) window.history.pushState({}, "", `/?project=${project.id}`);
    // The live research panel loads run history. Samples are opt-in only.
    if (version === requestVersion.current) setLoading(false);
  }
  function overview(updateUrl = true) {
    requestVersion.current++;
    setActive(null);
    setBrief(null);
    setLoading(false);
    setError("");
    if (updateUrl) window.history.pushState({}, "", "/");
  }

  async function loadWorkspace() {
    const list = await api<Project[]>("/projects");
    setProjects(list);
    const id = new URLSearchParams(window.location.search).get("project");
    const project = list.find((p) => p.id === id);
    if (project) await openProject(project, false);
  }
  useEffect(() => {
    api<User>("/auth/me")
      .then(async (value) => {
        setUser(value);
        await loadWorkspace();
      })
      .catch((e) => {
        if (!(e instanceof ApiError && e.status === 401)) failure(e);
      })
      .finally(() => setReady(true));
    // Initial session restoration only.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  useEffect(() => {
    function back() {
      const id = new URLSearchParams(window.location.search).get("project");
      const p = projects.find((item) => item.id === id);
      if (p) void openProject(p, false);
      else overview(false);
    }
    window.addEventListener("popstate", back);
    return () => window.removeEventListener("popstate", back);
  }, [projects]);
  useEffect(() => {
    if (creating) createDialog.current?.showModal();
    else createDialog.current?.close();
  }, [creating]);
  useEffect(() => {
    if (evidence) evidenceDialog.current?.showModal();
    else evidenceDialog.current?.close();
  }, [evidence]);

  async function authenticated(value: User) {
    setUser(value);
    setError("");
    try {
      await loadWorkspace();
    } catch (e) {
      failure(e);
    }
  }
  async function signOut() {
    try {
      await api("/auth/logout", {});
      requestVersion.current++;
      setUser(null);
      setProjects([]);
      setActive(null);
      setBrief(null);
      setEvidence(null);
      setCreating(false);
      window.history.replaceState({}, "", "/");
    } catch (e) {
      failure(e);
    }
  }
  async function createProject(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const data = Object.fromEntries(new FormData(form));
    setLoading(true);
    setError("");
    try {
      const p = await api<Project>("/projects", data);
      setProjects((old) => [p, ...old]);
      setCreating(false);
      form.reset();
      await openProject(p);
    } catch (e) {
      failure(e);
      setLoading(false);
    }
  }
  function exportBrief() {
    if (!brief) return;
    const text = [
      `# ${brief.title}`,
      brief.notice,
      `Project question: ${active?.question}`,
      ...brief.sections.flatMap((s) => [
        `\n## ${s.title}`,
        ...s.blocks.map(
          (b) =>
            `${b.text} ${b.evidence_ids.map((id) => `[${id}]`).join(" ")}${b.limitation ? `\nLimitation: ${b.limitation}` : ""}`,
        ),
      ]),
      ...(brief.competitors?.length
        ? [
            "\n## Competitor comparison",
            ...brief.competitors.flatMap((c) => [
              `### ${c.name}`,
              ...c.facts.map(
                (f) =>
                  `${f.dimension}: ${f.text} ${f.evidence_ids.map((id) => `[${id}]`).join(" ")}`,
              ),
            ]),
          ]
        : []),
      "\n## Evidence",
      ...brief.evidence.map(
        (e) =>
          `### ${e.id}: ${e.title}\n${e.kind} · ${e.location}\n${e.url || "Synthetic fixture"}\n> ${e.excerpt}\n${e.limitation}`,
      ),
      "\n## Limitations",
      ...brief.limitations,
    ].join("\n\n");
    const url = URL.createObjectURL(
      new Blob([text], { type: "text/markdown" }),
    );
    const a = document.createElement("a");
    a.href = url;
    a.download =
      brief.mode === "live"
        ? "fieldnotes-research-brief.md"
        : "fieldnotes-sample-brief.md";
    a.click();
    URL.revokeObjectURL(url);
  }

  if (!ready)
    return (
      <main className="initial">
        <Mark />
        <p>Opening your workspace…</p>
      </main>
    );
  if (!user)
    return <Auth onAuthenticated={authenticated} initialError={error} />;

  return (
    <div className="workspace">
      <aside className="sidebar">
        <button
          className="brand-button"
          onClick={() => overview()}
          aria-label="Fieldnotes home"
        >
          <Mark />
        </button>
        <div className="workspace-label">
          <span className="avatar small">{user.email[0].toUpperCase()}</span>
          <div>
            Personal workspace<small>Private research</small>
          </div>
          <ShieldCheck size={15} />
        </div>
        <p className="nav-label">WORKSPACE</p>
        <button
          className={`nav-item ${!active ? "selected" : ""}`}
          onClick={() => overview()}
        >
          <Folder size={17} /> All projects{" "}
          <span className="count">{projects.length}</span>
        </button>
        <div className="nav-section">
          <p className="nav-label">YOUR PROJECTS</p>
          <button
            className="icon-button"
            aria-label="Create project"
            onClick={() => {
              setError("");
              setCreating(true);
            }}
          >
            <Plus size={15} />
          </button>
        </div>
        <nav aria-label="Projects">
          {projects.map((p) => (
            <button
              key={p.id}
              className={`project-nav ${active?.id === p.id ? "current" : ""}`}
              onClick={() => void openProject(p)}
            >
              <span className="project-dot" />
              {p.name}
            </button>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="milestone">
            <FlaskConical size={18} />
            <div>
              Research, with receipts.<p>Every insight has a source.</p>
            </div>
          </div>
          <div className="account">
            <span className="avatar">{user.email[0].toUpperCase()}</span>
            <span className="account-email" title={user.email}>
              {user.email}
              <small>Local development account</small>
            </span>
            <button
              className="icon-button"
              aria-label="Sign out"
              onClick={() => void signOut()}
            >
              <LogOut size={17} />
            </button>
          </div>
        </div>
      </aside>
      <div className="main-shell">
        <header className="topbar">
          <div className="breadcrumbs">
            <span>Workspace</span>
            <ChevronRight size={14} />
            <button onClick={() => overview()}>Projects</button>
            {active && (
              <>
                <ChevronRight size={14} />
                <strong>{active.name}</strong>
              </>
            )}
          </div>
          <span className="private">
            <ShieldCheck size={14} /> Private workspace
          </span>
          <button className="mobile-signout" onClick={() => void signOut()}>
            Sign out
          </button>
        </header>
        <main className="content">
          {error && (
            <div role="alert" className="error">
              {error}
            </div>
          )}
          {!active ? (
            <>
              <div className="page-heading">
                <div>
                  <p className="eyebrow">YOUR RESEARCH, CONNECTED</p>
                  <h1>
                    A little evidence.
                    <br />A clearer direction.
                  </h1>
                  <p className="lede">
                    A home for the questions worth asking — and the evidence
                    behind your next move.
                  </p>
                </div>
                <button
                  className="button primary"
                  onClick={() => {
                    setError("");
                    setCreating(true);
                  }}
                >
                  <Plus size={17} /> New project
                </button>
              </div>
              <div className="welcome-strip">
                <span className="strip-icon">
                  <BookOpen size={22} />
                </span>
                <div>
                  <strong>Start with a question. Follow the evidence.</strong>
                  <p>
                    Create a project, connect AI, and send your research team to
                    investigate your question.
                  </p>
                </div>
                <span className="pill">MULTI-AGENT RESEARCH</span>
              </div>
              <div className="section-toolbar">
                <h2>
                  Your projects{" "}
                  <span>{projects.length.toString().padStart(2, "0")}</span>
                </h2>
                <label className="search">
                  <Search size={16} />
                  <input
                    aria-label="Search projects"
                    placeholder="Find a project…"
                    value={filter}
                    onChange={(e) => setFilter(e.target.value)}
                  />
                </label>
              </div>
              {projects.length === 0 ? (
                <div className="empty-state">
                  <span className="empty-icon">
                    <Folder size={29} />
                  </span>
                  <h3>Good research starts here.</h3>
                  <p>
                    What do you want to understand?
                    <br />
                    Give your first question a place to grow.
                  </p>
                  <button
                    className="button primary"
                    onClick={() => setCreating(true)}
                  >
                    <Plus size={16} /> Create your first project
                  </button>
                  <small>Connect AI to run live research</small>
                </div>
              ) : (
                <div className="project-grid">
                  {projects
                    .filter((p) =>
                      p.name.toLowerCase().includes(filter.toLowerCase()),
                    )
                    .map((p) => (
                      <button
                        key={p.id}
                        className="project-card"
                        onClick={() => void openProject(p)}
                      >
                        <div className="card-top">
                          <span className="folder-tile">
                            <Folder size={22} />
                          </span>
                          <ArrowUpRight size={19} />
                        </div>
                        <h3>{p.name}</h3>
                        <p>{p.question}</p>
                        <div className="card-tags">
                          <span>{p.geography || "Any geography"}</span>
                          <span>Research workspace</span>
                        </div>
                        <div className="card-footer">
                          <span>
                            Created{" "}
                            {new Date(p.created_at * 1000).toLocaleDateString(
                              undefined,
                              { month: "short", day: "numeric" },
                            )}
                          </span>
                          <span>
                            Open project <ArrowRight size={14} />
                          </span>
                        </div>
                      </button>
                    ))}
                  {projects.filter((p) =>
                    p.name.toLowerCase().includes(filter.toLowerCase()),
                  ).length === 0 && (
                    <p className="muted">No projects match “{filter}”.</p>
                  )}
                </div>
              )}
              <p className="workspace-note">
                <ShieldCheck size={14} /> Only you can access the projects in
                this workspace.
              </p>
            </>
          ) : (
            <>
              <div className="project-header">
                <div>
                  <p className="eyebrow">RESEARCH PROJECT</p>
                  <h1 className="project-title">{active.name}</h1>
                  <p className="project-question">{active.question}</p>
                  <div className="project-meta">
                    <span>{active.audience || "Audience not specified"}</span>
                    <span>·</span>
                    <span>{active.geography || "Any geography"}</span>
                  </div>
                </div>
                <button
                  className="button secondary"
                  onClick={exportBrief}
                  disabled={!brief}
                >
                  <ArrowDownToLine size={16} />{" "}
                  {brief?.mode === "live" ? "Export brief" : "Export sample"}
                </button>
              </div>
              <ResearchPanel
                key={active.id}
                project={active}
                onBrief={setBrief}
                onError={failure}
              />
              <div className="tabbar">
                <span className="active-tab">
                  <FileText size={16} /> Research brief
                </span>
                <span className="tab-info">
                  {brief
                    ? brief.mode === "live"
                      ? "Live research · Evidence reviewed by AI"
                      : "Synthetic example"
                    : "Awaiting research"}
                </span>
              </div>
              {loading && (
                <p role="status" className="loading">
                  Opening project…
                </p>
              )}
              {brief && (
                <>
                  <div className="fixture-notice">
                    <FlaskConical size={20} />
                    <div>
                      <strong>
                        {brief.mode === "live"
                          ? "Research for your question, with visible limitations."
                          : "Sample data, transparent by design."}
                      </strong>
                      <p>{brief.notice}</p>
                    </div>
                    <span className="pill amber">
                      {brief.mode === "live" ? "AI RESEARCH" : "SYNTHETIC"}
                    </span>
                  </div>
                  <div className="brief-layout">
                    <article className="paper">
                      <div className="paper-heading">
                        <span className="eyebrow">
                          PRODUCT DISCOVERY / RESEARCH BRIEF
                        </span>
                        <span className="status">
                          <Check size={13} />{" "}
                          {brief.mode === "live"
                            ? "AI reviewed"
                            : "Fixture ready"}
                        </span>
                      </div>
                      <h2 className="brief-title">{brief.title}</h2>
                      <p className="brief-subtitle">{brief.subtitle}</p>
                      <div className="brief-stats">
                        <span>
                          <FileText size={15} />
                          {brief.sections.length} sections
                        </span>
                        <span>
                          <BookOpen size={15} />
                          {brief.evidence.length} evidence excerpts
                        </span>
                        <span>
                          <ShieldCheck size={15} /> Traceable evidence
                        </span>
                      </div>
                      {brief.sections.map((s) => (
                        <section key={s.id} id={s.id} className="brief-section">
                          <p className="eyebrow">{s.eyebrow}</p>
                          <h3>{s.title}</h3>
                          {s.blocks.map((b) => (
                            <div key={b.id} className={`claim claim-${b.type}`}>
                              <span className={`type-label type-${b.type}`}>
                                {b.type}
                              </span>
                              <p>
                                {b.text}{" "}
                                {b.evidence_ids.map((id) => {
                                  const e = brief.evidence.find(
                                    (v) => v.id === id,
                                  );
                                  return e ? (
                                    <button
                                      className="citation"
                                      key={id}
                                      aria-label={`View evidence ${id}`}
                                      onClick={() => setEvidence(e)}
                                    >
                                      {brief.evidence.indexOf(e) + 1}
                                    </button>
                                  ) : null;
                                })}
                              </p>
                              {b.limitation && (
                                <small className="claim-limitation">
                                  {b.limitation}
                                </small>
                              )}
                            </div>
                          ))}
                        </section>
                      ))}
                      {brief.competitors && brief.competitors.length > 0 && (
                        <CompetitorTable
                          competitors={brief.competitors}
                          evidence={brief.evidence}
                          onEvidence={setEvidence}
                        />
                      )}
                      <section id="limitations" className="limitations">
                        <h3>What this brief cannot tell you</h3>
                        <ul>
                          {brief.limitations.map((l) => (
                            <li key={l}>{l}</li>
                          ))}
                        </ul>
                      </section>
                    </article>
                    <aside className="brief-aside">
                      <div className="aside-section">
                        <p className="eyebrow">IN THIS BRIEF</p>
                        {brief.sections.map((s, i) => (
                          <a key={s.id} href={`#${s.id}`}>
                            <span>0{i + 1}</span>
                            {s.title}
                          </a>
                        ))}
                        <a href="#limitations">
                          <span>06</span>Limitations
                        </a>
                      </div>
                      <div className="evidence-card">
                        <BookOpen size={21} />
                        <h3>Show your sources.</h3>
                        <p>
                          Select any numbered citation to see the exact excerpt,
                          source and limitation behind it.
                        </p>
                        <div className="source-list">
                          {brief.evidence.map((e, i) => (
                            <button key={e.id} onClick={() => setEvidence(e)}>
                              <span className="source-number">{i + 1}</span>
                              <span>
                                {e.title}
                                <small>{e.kind}</small>
                              </span>
                              <ArrowUpRight size={14} />
                            </button>
                          ))}
                        </div>
                      </div>
                      <div className="next-card">
                        <Sparkles size={17} />
                        <strong>
                          {brief.mode === "live"
                            ? "Review before deciding"
                            : "A synthetic example"}
                        </strong>
                        <p>
                          {brief.mode === "live"
                            ? "The reviewer is an AI agent, not a human. Evidence support does not establish market demand or completeness."
                            : "This example is separate from live research and does not answer your saved question."}
                        </p>
                      </div>
                    </aside>
                  </div>
                </>
              )}
            </>
          )}
        </main>
        <footer className="footer">
          <span>
            fieldnotes. <span>Evidence before assumptions.</span>
          </span>
          <span>Local MVP · Multi-agent research</span>
        </footer>
      </div>
      <dialog
        ref={createDialog}
        className="create-dialog"
        aria-label="Create a project"
        onCancel={() => setCreating(false)}
        onClose={() => setCreating(false)}
      >
        <div className="dialog-heading">
          <span className="folder-tile">
            <Folder size={22} />
          </span>
          <button
            className="icon-button"
            aria-label="Close new project"
            onClick={() => setCreating(false)}
          >
            <X size={20} />
          </button>
        </div>
        <p className="eyebrow">A NEW LINE OF INQUIRY</p>
        <h2>Create a project</h2>
        <p className="muted">
          Save your question, then let your research team investigate the
          market, alternatives and opportunities.
        </p>
        <form onSubmit={createProject}>
          <label>
            Project name
            <input
              name="name"
              required
              maxLength={120}
              placeholder="e.g. Freelancer finance discovery"
              autoFocus
            />
          </label>
          <label>
            Research question
            <textarea
              name="question"
              required
              minLength={10}
              maxLength={3000}
              rows={3}
              placeholder="What do you want to understand?"
            />
          </label>
          <div className="form-row">
            <label>
              Audience <span>optional</span>
              <input
                name="audience"
                maxLength={200}
                placeholder="e.g. Freelancers"
              />
            </label>
            <label>
              Geography <span>optional</span>
              <input
                name="geography"
                maxLength={100}
                placeholder="e.g. India"
              />
            </label>
          </div>
          <div className="form-note">
            <Search size={16} /> Connect AI inside your project to start a live
            research plan.
          </div>
          {error && (
            <p role="alert" className="error">
              {error}
            </p>
          )}
          <button className="button primary full" disabled={loading}>
            {loading ? "Creating project…" : "Create project"}
            <ArrowRight size={16} />
          </button>
        </form>
      </dialog>
      <dialog
        ref={evidenceDialog}
        className="evidence-dialog"
        aria-labelledby="evidence-title"
        onCancel={() => setEvidence(null)}
        onClose={() => setEvidence(null)}
      >
        {evidence && (
          <>
            <div className="drawer-top">
              <span className="eyebrow">THE EVIDENCE BEHIND THE INSIGHT</span>
              <button
                className="icon-button"
                aria-label="Close evidence"
                onClick={() => setEvidence(null)}
              >
                <X size={21} />
              </button>
            </div>
            <span className="pill amber">
              {evidence.url
                ? "LIVE SOURCE EXCERPT"
                : evidence.kind === "Supplied customer notes"
                  ? "CUSTOMER NOTES"
                  : "SYNTHETIC EVIDENCE"}
            </span>
            <h2 id="evidence-title">{evidence.title}</h2>
            <p className="evidence-location">
              {evidence.kind} · {evidence.location}
            </p>
            <div className="quote-mark">“</div>
            <blockquote>{evidence.excerpt}</blockquote>
            <div className="source-detail">
              <span>SOURCE ID</span>
              <code>{evidence.source_id}</code>
              <span>EVIDENCE ID</span>
              <code>{evidence.id}</code>
              <span>PROVENANCE</span>
              <p>
                {evidence.url ? (
                  <a
                    href={evidence.url}
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    Open original source
                  </a>
                ) : evidence.kind === "Supplied customer notes" ? (
                  "Customer notes supplied for this run"
                ) : (
                  "Bundled demonstration fixture · version 1"
                )}
              </p>
              {evidence.retrieved_at && (
                <>
                  <span>COLLECTED</span>
                  <p>
                    {new Date(evidence.retrieved_at * 1000).toLocaleString()}
                  </p>
                </>
              )}
            </div>
            <div className="evidence-warning">
              <ShieldCheck size={19} />
              <div>
                <strong>Know the limits</strong>
                <p>{evidence.limitation}</p>
              </div>
            </div>
            <button
              className="button secondary full"
              onClick={() => setEvidence(null)}
            >
              Back to brief
              <ArrowRight size={16} />
            </button>
          </>
        )}
      </dialog>
    </div>
  );
}

function Auth({
  onAuthenticated,
  initialError,
}: {
  onAuthenticated: (user: User) => Promise<void>;
  initialError: string;
}) {
  const [register, setRegister] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(initialError);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = Object.fromEntries(new FormData(event.currentTarget));
    setBusy(true);
    setError("");
    try {
      const value = await api<User>(
        register ? "/auth/register" : "/auth/login",
        data,
      );
      await onAuthenticated(value);
    } catch (e) {
      setError(
        e instanceof Error ? e.message : "Could not connect. Please retry.",
      );
    } finally {
      setBusy(false);
    }
  }
  return (
    <main className="auth-page">
      <section className="auth-story">
        <Mark />
        <div className="auth-story-content">
          <span className="auth-kicker">
            <span /> THE PRODUCT RESEARCH WORKSPACE
          </span>
          <h1>
            Better questions.
            <br />
            Stronger evidence.
            <br />
            <em>Clearer decisions.</em>
          </h1>
          <p>
            Bring your research into focus. Connect what you learn to the
            evidence that makes it matter.
          </p>
          <div className="auth-sample">
            <div>
              <BookOpen size={19} />
              <span>FROM EVIDENCE TO INSIGHT</span>
              <span className="sample-citation">1</span>
            </div>
            <p>
              “I keep a separate sheet for invoices. Every Friday I check which
              ones are still unpaid…”
            </p>
            <small>Synthetic interview · Sample evidence</small>
          </div>
        </div>
        <div className="auth-bottom">
          <ShieldCheck size={15} /> Your workspace. Your research.
        </div>
      </section>
      <section className="auth-form-panel">
        <div className="auth-form">
          <span className="welcome-icon">
            <Leaf size={27} />
          </span>
          <p className="eyebrow">A PLACE TO THINK CLEARLY</p>
          <h2>
            {register ? "Make room for discovery." : "Welcome to Fieldnotes."}
          </h2>
          <p className="muted">
            {register
              ? "Create a local account to start your research workspace."
              : "Sign in to pick up where your questions left off."}
          </p>
          <form onSubmit={submit}>
            <label>
              Email address
              <input
                name="email"
                type="email"
                autoComplete="email"
                required
                maxLength={254}
                placeholder="you@example.com"
              />
            </label>
            <label>
              Password
              <input
                name="password"
                type="password"
                autoComplete={register ? "new-password" : "current-password"}
                minLength={12}
                maxLength={128}
                required
                placeholder="At least 12 characters"
              />
            </label>
            {error && (
              <p role="alert" className="error">
                {error}
              </p>
            )}
            <button className="button primary full" disabled={busy}>
              {busy
                ? "Opening workspace…"
                : register
                  ? "Create account"
                  : "Sign in"}
              <ArrowRight size={17} />
            </button>
          </form>
          <p className="auth-toggle">
            {register ? "Already have an account?" : "New to Fieldnotes?"}{" "}
            <button
              onClick={() => {
                setRegister(!register);
                setError("");
              }}
            >
              {register ? "Sign in" : "Create an account"}
            </button>
          </p>
          <div className="local-note">
            <FlaskConical size={17} />
            <p>
              <strong>Local development preview</strong>No email verification or
              password recovery yet. Use a development-only password. Connect an
              AI API key after sign-in for live research.
            </p>
          </div>
        </div>
        <span className="auth-footer">
          Built for thoughtful product discovery.
        </span>
      </section>
    </main>
  );
}
