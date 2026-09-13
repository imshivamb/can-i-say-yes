"use client";

import { useEffect, useState } from "react";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8080";
const RECORDED = process.env.NEXT_PUBLIC_RECORDED === "1";
const REQUEST_TEXT =
  "We'd like 12 social creatives, a landing page and three short videos for our September campaign. Can you have everything ready by September 18 for ₹4.2 lakh?";
type ExampleKey = "acme" | "nova";
const EXAMPLES: Record<ExampleKey, {
  customer: string;
  initials: string;
  scope: string;
  request: string;
  date: string;
  budget: string;
}> = {
  acme: {
    customer: "Acme Foods",
    initials: "AF",
    scope: "September campaign",
    request: REQUEST_TEXT,
    date: "18 September",
    budget: "₹4,20,000",
  },
  nova: {
    customer: "Nova Health",
    initials: "NH",
    scope: "Product launch site",
    request: "Can Northstar build our product launch site with six pages by October 9 for ₹5.2 lakh?",
    date: "09 October",
    budget: "₹5,20,000",
  },
};

type Assessment = {
  decision: string;
  confidence?: number;
  reasons: { title: string; detail: string; evidence_ids: string[] }[];
  alternatives: {
    id: string;
    title: string;
    summary: string;
    extra_cost: { amount: number };
    recommended?: boolean;
  }[];
};

type Decision = {
  id: string;
  commitment_id?: string | null;
  status?: string;
  recommended_option_id?: string | null;
  reason: string;
  options?: { id: string; title: string; summary: string; extra_cost: { amount: number } }[];
};
type Commitment = {
  id?: string;
  request_id?: string;
  health?: string | null;
  committed_deadline?: string;
  current_forecast?: string | null;
};
type StoredDecision = { status: string };
type Clock = { now: string };
type ActivityRecord = { text: string };

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
  });
  if (!response.ok) throw new Error(await response.text());
  return response.json();
}

export default function Home() {
  const [assessment, setAssessment] = useState<Assessment | null>(null);
  const [decision, setDecision] = useState<Decision | null>(null);
  const [activity, setActivity] = useState<string[]>([]);
  const [message, setMessage] = useState("Your autopilot is standing by.");
  const [busy, setBusy] = useState(false);
  const [approved, setApproved] = useState(false);
  const [riskDetected, setRiskDetected] = useState(false);
  const [error, setError] = useState("");
  const [activeNav, setActiveNav] = useState("Autopilot");
  const [selectedExample, setSelectedExample] = useState<ExampleKey>("acme");
  const [selectedOption, setSelectedOption] = useState<string | null>(null);
  const [commitments, setCommitments] = useState<Commitment[]>([]);
  const [decisions, setDecisions] = useState<StoredDecision[]>([]);
  const [clock, setClock] = useState<Clock | null>(null);
  const [riskDecision, setRiskDecision] = useState<Decision | null>(null);
  const [riskCommitment, setRiskCommitment] = useState<Commitment | null>(null);
  const [riskApproved, setRiskApproved] = useState(false);

  async function refreshDashboard() {
    const [commitmentItems, decisionItems, activityItems, clockItem] = await Promise.all([
      request<Commitment[]>("/api/commitments"),
      request<StoredDecision[]>("/api/decisions"),
      request<ActivityRecord[]>("/api/activity"),
      request<Clock>("/api/clock"),
    ]);
    setCommitments(commitmentItems);
    setDecisions(decisionItems);
    setActivity(activityItems.map((item) => item.text));
    setClock(clockItem);
  }

  async function loadRiskDecision() {
    const [openDecisions, currentCommitments] = await Promise.all([
      request<Decision[]>("/api/decisions"),
      request<Commitment[]>("/api/commitments"),
    ]);
    const opened = openDecisions.find(
      (item) => item.status === "OPEN" && item.commitment_id,
    );
    setRiskDecision(opened ?? null);
    setRiskCommitment(
      opened
        ? currentCommitments.find((item) => item.id === opened.commitment_id) ?? null
        : null,
    );
    setSelectedOption(opened?.recommended_option_id ?? null);
  }

  useEffect(() => {
    refreshDashboard().catch(() => undefined);
  }, []);

  function navigate(label: string, target: string) {
    setActiveNav(label);
    document.getElementById(target)?.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  async function assess() {
    setBusy(true);
    setError("");
    setMessage("Investigator is checking the operating picture…");
    try {
      const created = await request<{ request: { id: string } }>("/api/requests", {
        method: "POST",
        body: JSON.stringify({
          text: EXAMPLES[selectedExample].request,
          recorded: RECORDED,
          example: selectedExample,
        }),
      });
      const result = await request<{ assessment: Assessment; decision: Decision }>(
        `/api/requests/${created.request.id}/assess?recorded=${RECORDED}`,
        { method: "POST" },
      );
      setAssessment(result.assessment);
      setDecision(result.decision);
      setSelectedOption(
        result.decision.recommended_option_id ?? result.assessment.alternatives[0]?.id ?? null,
      );
      await refreshDashboard();
      setMessage("Investigation complete. One decision needs your attention.");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Something went wrong");
      setMessage("The investigation could not be completed.");
    } finally {
      setBusy(false);
    }
  }

  async function approve() {
    if (!decision) return;
    setBusy(true);
    try {
      await request(`/api/decisions/${decision.id}/approve`, {
        method: "POST",
        body: JSON.stringify({ option_id: selectedOption ?? decision.recommended_option_id ?? "alt_a" }),
      });
      setApproved(true);
      await refreshDashboard();
      setMessage("Commitment created. Northstar is now watching it in the background.");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Approval failed");
    } finally {
      setBusy(false);
    }
  }

  const selectedOptionIndex =
    assessment?.alternatives.findIndex((option) => option.id === selectedOption) ?? -1;
  const selectedOptionLabel =
    selectedOptionIndex >= 0 ? `Option ${String.fromCharCode(65 + selectedOptionIndex)}` : "selected option";

  async function simulateSupplierEmail() {
    setBusy(true);
    try {
      const result = await request<{ opened_decisions: number }>("/api/events/inbound", {
        method: "POST",
        body: JSON.stringify({
          event_id: `evt_demo_${Date.now()}`,
          summary: "Frame & Grain: editor availability slipped to September 20",
          source_reference: "gmail:demo-supplier-delay",
          payload: { supplier_id: "sup_frame_grain", available_from: "2026-09-20" },
        }),
      });
      setRiskDetected(result.opened_decisions > 0);
      await refreshDashboard();
      if (result.opened_decisions > 0) await loadRiskDecision();
      setMessage("Monitor woke up from the supplier email and caught the delivery risk.");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Supplier update failed");
    } finally {
      setBusy(false);
    }
  }

  async function approveRisk() {
    if (!riskDecision || !selectedOption) return;
    setBusy(true);
    try {
      await request(`/api/decisions/${riskDecision.id}/approve`, {
        method: "POST",
        body: JSON.stringify({ option_id: selectedOption }),
      });
      setRiskApproved(true);
      await refreshDashboard();
      setMessage("Backup capacity approved. The commitment is back on track.");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Risk approval failed");
    } finally {
      setBusy(false);
    }
  }

  async function advanceTime() {
    setBusy(true);
    try {
      const result = await request<{ opened_decisions: number }>("/api/clock/advance", {
        method: "POST",
        body: JSON.stringify({ to: "supplier_delay", recorded: RECORDED }),
      });
      setRiskDetected(result.opened_decisions > 0);
      await refreshDashboard();
      if (result.opened_decisions > 0) await loadRiskDecision();
      setMessage("The simulation clock advanced and the Monitor checked affected commitments.");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not advance time");
    } finally {
      setBusy(false);
    }
  }

  async function resetDemo() {
    setBusy(true);
    try {
      await request("/api/demo/reset", { method: "POST" });
      setAssessment(null);
      setDecision(null);
      setApproved(false);
      setRiskDetected(false);
      setRiskDecision(null);
      setRiskCommitment(null);
      setRiskApproved(false);
      await refreshDashboard();
      setMessage("Your autopilot is standing by.");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not reset demo");
    } finally {
      setBusy(false);
    }
  }

  const monitoredCount = commitments.length;
  const onTrackCount = commitments.filter((item) => item.health === "ON_TRACK").length;
  const atRiskCount = commitments.filter((item) => item.health === "AT_RISK").length;
  const needsYouCount = decisions.filter((item) => item.status === "OPEN").length;
  const routineActionsCount = activity.filter(
    (item) => !/decision|approved|commitment created/i.test(item),
  ).length;
  const humanDecisionCount = decisions.length;
  const clockDate = clock ? new Date(clock.now) : null;
  const dateLabel = clockDate
    ? clockDate.toLocaleDateString("en-IN", { weekday: "long", day: "numeric", month: "long", year: "numeric" })
    : "Loading operating clock…";
  const timeLabel = clockDate
    ? clockDate.toLocaleTimeString("en-IN", { hour: "numeric", minute: "2-digit" })
    : "—";

  return (
    <main className="app-shell">
      <aside className="sidebar">
        <div className="brand-lockup">
          <div className="brand-mark">↗</div>
          <div><strong>can i say yes?</strong><span>northstar creative</span></div>
        </div>
        <nav>
          <p className="nav-label">WORKSPACE</p>
          <button className={`nav-item ${activeNav === "Autopilot" ? "active" : ""}`} onClick={() => navigate("Autopilot", "autopilot")}><span>◈</span> Autopilot <b>{needsYouCount}</b></button>
          <button className={`nav-item ${activeNav === "Commitments" ? "active" : ""}`} onClick={() => navigate("Commitments", "metrics")}><span>◌</span> Commitments <b>{monitoredCount}</b></button>
          <button className={`nav-item ${activeNav === "Evidence" ? "active" : ""}`} onClick={() => navigate("Evidence", "decisions")}><span>⌁</span> Evidence</button>
          <button className={`nav-item ${activeNav === "Activity" ? "active" : ""}`} onClick={() => navigate("Activity", "activity")}><span>↗</span> Activity</button>
          <p className="nav-label nav-spacer">SYSTEM</p>
          <button className={`nav-item ${activeNav === "Connections" ? "active" : ""}`} onClick={() => navigate("Connections", "connections")}><span>◒</span> Connections <i className="live-dot" /></button>
          <button className={`nav-item ${activeNav === "Settings" ? "active" : ""}`} onClick={() => navigate("Settings", "settings")}><span>⚙</span> Settings</button>
        </nav>
        <div className="sidebar-bottom">
          <div className="agent-orb"><span /></div>
          <div><strong>Agent online</strong><small>Monitoring Northstar</small></div>
          <span className="pulse" />
        </div>
      </aside>

      <section className="workspace">
        <header className="topbar">
          <div className="crumbs"><span>Northstar Creative</span><b>/</b><strong>Autopilot</strong></div>
          <div className="top-actions">
            <span className="sync"><i className="live-dot" /> Last synced just now</span>
            <button className="icon-button">?</button><div className="avatar">PS</div>
          </div>
        </header>

        <div className="content" id="autopilot">
          <section className="welcome-row">
            <div>
              <div className="eyebrow green-eyebrow"><span className="spark">✦</span> {dateLabel.toUpperCase()}</div>
              <h1>Good morning, Rohan<span>.</span></h1>
              <p className="intro">{message}</p>
            </div>
            <div className="date-control"><span>◷</span> {timeLabel} <button className="ghost-button" onClick={advanceTime} disabled={busy}>Advance time</button><button className="ghost-button" onClick={resetDemo} disabled={busy}>Reset</button></div>
          </section>

          <section className="metric-grid" id="metrics">
            <div className="metric-card metric-primary"><span className="metric-icon">◉</span><div><small>COMMITMENTS MONITORED</small><strong>{monitoredCount}</strong><em>From operating state</em></div><div className="mini-ring">LIVE</div></div>
            <div className="metric-card"><span className="metric-icon calm-icon">✓</span><div><small>ON TRACK</small><strong>{onTrackCount}</strong><em className="positive">Current health</em></div></div>
            <div className="metric-card"><span className="metric-icon warning-icon">!</span><div><small>AT RISK</small><strong>{atRiskCount}</strong><em className="warning-text">Needs monitoring</em></div></div>
            <div className="metric-card"><span className="metric-icon danger-icon">◈</span><div><small>NEEDS YOU</small><strong>{needsYouCount}</strong><em className="danger-text">{needsYouCount ? "Decision waiting" : "All clear"}</em></div></div>
          </section>

          {error && <div className="error-banner">⚠ {error}</div>}
          {approved && (
            <div className="success-banner" role="status">
              <div className="success-mark">✓</div>
              <div>
                <strong>{selectedOptionLabel} approved successfully</strong>
                <p>Commitment created · customer response queued · background monitoring is active.</p>
              </div>
              <span className="success-status">COMMITTED</span>
            </div>
          )}

          <section className="section-heading" id="decisions">
            <div><span className="section-kicker">ATTENTION REQUIRED</span><h2>Decisions waiting for you</h2></div>
            <span className="live-label"><i className="live-dot" /> LIVE OPERATIONS</span>
          </section>

          {riskDecision && riskCommitment ? (
            <section className="decision-layout">
              <article className="decision-card card-surface">
                <div className="decision-top"><div className="customer-mark">AF</div><div className="customer-name"><strong>Acme Foods</strong><span>Background Monitor · Supplier update</span></div><span className="status-pill status-danger"><i /> AT RISK</span></div>
                <div className="decision-title"><div><span className="section-kicker">MONITOR FINDING</span><h3>Commitment needs attention.</h3></div></div>
                <div className="promise-strip"><div><small>COMMITTED</small><b>{riskCommitment.committed_deadline}</b></div><div><small>FORECAST</small><b>{riskCommitment.current_forecast ?? "—"}</b></div><div><small>STATUS</small><b>{riskApproved ? "ON TRACK" : "AT RISK"}</b></div></div>
                <div className="reasons-list"><div className="reason-row"><span className="reason-number reason-1">01</span><div><strong>Supplier delay detected</strong><p>{riskDecision.reason}</p><small>⌁ Monitor evidence verified</small></div></div></div>
                <div className="decision-footer"><div><span className="agent-status"><i className="live-dot" /> Monitor complete</span><span className="evidence-count">⌁ Human decision required</span></div><button className="primary-button" onClick={approveRisk} disabled={busy || riskApproved}>{riskApproved ? "APPROVED · ON TRACK" : busy ? "APPROVING…" : "APPROVE BACKUP CAPACITY"} <span>↗</span></button></div>
              </article>
              <aside className="options-card card-surface">
                <div className="side-card-heading"><div><span className="section-kicker">RECOMMENDATION</span><h3>Choose a way to protect delivery</h3></div><span className="option-count">{riskDecision.options?.length ?? 0} OPTIONS</span></div>
                <div className="option-list">
                  {(riskDecision.options ?? []).map((option) => (
                    <button type="button" className={`option-row ${selectedOption === option.id ? "selected recommended" : ""}`} key={option.id} onClick={() => setSelectedOption(option.id)} disabled={busy || riskApproved}>
                      <div className="option-copy"><strong>{option.title}</strong><p>{option.summary}</p></div>
                      <div className="option-meta"><b>₹{option.extra_cost.amount.toLocaleString("en-IN")}</b><span className="option-check">{selectedOption === option.id ? "✓ SELECTED" : "SELECT"}</span></div>
                    </button>
                  ))}
                </div>
              </aside>
            </section>
          ) : !assessment ? (
            <section className="empty-command card-surface">
              <div className="empty-glow" /><div className="empty-icon">✦</div>
              <div className="empty-copy">
                <span className="tag purple-tag">NEW CUSTOMER REQUEST</span>
                <h3>{EXAMPLES[selectedExample].customer} wants to move fast.</h3>
                <p>{selectedExample === "acme" ? "12 social creatives, a landing page and three short videos." : "A six-page product launch site."} Requested delivery <b>{EXAMPLES[selectedExample].date}</b>.</p>
                <div className="request-meta"><span>{EXAMPLES[selectedExample].budget} budget</span><span>·</span><span>Received 8 min ago</span></div>
              </div>
              <button className="primary-button" onClick={assess} disabled={busy}>{busy ? "INVESTIGATING…" : "CHECK FEASIBILITY"} <span>↗</span></button>
              <button className="example-switch" onClick={() => setSelectedExample(selectedExample === "acme" ? "nova" : "acme")} disabled={busy}>Try {selectedExample === "acme" ? "Nova Health" : "Acme Foods"} →</button>
            </section>
          ) : (
            <section className="decision-layout">
              <article className="decision-card card-surface">
                <div className="decision-top"><div className="customer-mark">{EXAMPLES[selectedExample].initials}</div><div className="customer-name"><strong>{EXAMPLES[selectedExample].customer}</strong><span>{EXAMPLES[selectedExample].scope} · New commitment</span></div><span className={`status-pill ${assessment.decision === "SAFE" ? "status-calm" : "status-danger"}`}><i /> {assessment.decision}</span></div>
                <div className="decision-title"><div><span className="section-kicker">INVESTIGATOR FINDING</span><h3>{assessment.decision === "SAFE" ? "The requested promise can be kept." : "The requested promise needs a safer path."}</h3></div><div className="confidence"><span>MODEL CONFIDENCE</span><strong>{Math.round((assessment.confidence ?? 0) * 100)}%</strong><div><i /></div></div></div>
                <div className="promise-strip"><div><small>REQUESTED DELIVERY</small><b>{EXAMPLES[selectedExample].date}</b></div><div><small>PROJECT VALUE</small><b>{EXAMPLES[selectedExample].budget}</b></div><div><small>SCOPE</small><b>{selectedExample === "acme" ? "16 deliverables" : "6 pages"}</b></div></div>
                <div className="reasons-list">{assessment.reasons.slice(0, 4).map((reason, index) => <div className="reason-row" key={reason.title}><span className={`reason-number reason-${index + 1}`}>0{index + 1}</span><div><strong>{reason.title}</strong><p>{reason.detail}</p><small>⌁ {reason.evidence_ids.length} evidence sources verified</small></div><span className="reason-arrow">↗</span></div>)}</div>
                <div className="decision-footer"><div><span className="agent-status"><i className="live-dot" /> Investigator complete</span><span className="evidence-count">⌁ {assessment.reasons.length} material findings</span></div><button className="primary-button" onClick={approve} disabled={busy || approved}>{approved ? "APPROVED · MONITORING" : busy ? "SENDING…" : "APPROVE SELECTED OPTION"} <span>↗</span></button></div>
              </article>
              <aside className="options-card card-surface">
                <div className="side-card-heading"><div><span className="section-kicker">SAFER PATHS</span><h3>Choose a way forward</h3></div><span className="option-count">3 OPTIONS</span></div>
                <div className="option-list">
                  {assessment.alternatives.map((option, index) => (
                    <button
                      type="button"
                      className={`option-row ${option.recommended ? "recommended" : ""} ${selectedOption === option.id ? "selected" : ""}`}
                      key={option.id}
                      aria-pressed={selectedOption === option.id}
                      disabled={busy || approved}
                      onClick={() => setSelectedOption(option.id)}
                    >
                      <span className="option-letter">{String.fromCharCode(65 + index)}</span>
                      <div className="option-copy">
                        <strong>{option.title}</strong>
                        <p>{option.summary}</p>
                      </div>
                      <div className="option-meta">
                        <b>{option.extra_cost.amount === 0 ? "₹0" : `₹${option.extra_cost.amount.toLocaleString("en-IN")}`}</b>
                        {option.recommended && <span className="recommended-label">RECOMMENDED</span>}
                        <span className="option-check">{selectedOption === option.id ? "✓ SELECTED" : "SELECT"}</span>
                      </div>
                    </button>
                  ))}
                </div>
                {decision && <div className="approval-note"><span>✦</span><p><b>Human approval required</b><br />The agent can investigate and recommend. You decide what Northstar promises.</p></div>}
              </aside>
            </section>
          )}

          <section className="section-heading lower-heading"><div><span className="section-kicker">AUTOPILOT MONITOR</span><h2>Quietly working in the background</h2></div><button className="ghost-button" onClick={simulateSupplierEmail} disabled={busy}>{busy ? "PROCESSING…" : "↗ SEND TEST SUPPLIER UPDATE"}</button></section>
          <section className="bottom-grid">
            <div className="timeline-card card-surface" id="activity"><div className="side-card-heading"><div><span className="section-kicker">RECENT ACTIVITY</span><h3>What your agent handled</h3></div><span className="muted-small">TODAY</span></div><div className="timeline">{(activity.length ? activity.slice(-5) : ["Waiting for a request to investigate"]).map((item, index) => <div className="timeline-item" key={`${item}-${index}`}><span className={`timeline-dot ${index === 0 ? "active-dot" : ""}`} /><div><p>{item}</p><small>{index === 0 ? "Just now" : `${index * 2 + 1} min ago`}</small></div></div>)}</div></div>
            <div className={`risk-card card-surface ${riskDetected ? "risk-live" : ""}`} id="connections"><div className="risk-art"><div className="risk-orb">◒</div><span className="orbit orbit-one" /><span className="orbit orbit-two" /></div><div><span className="section-kicker">{riskDetected ? "MONITOR ALERT" : "AUTONOMOUS MONITORING"}</span><h3>{riskDetected ? "A commitment needs attention." : "Your commitments are covered."}</h3><p>{riskDetected ? "Supplier delay detected. The Monitor has opened a decision without another investigation request." : "The Monitor checks changing suppliers, calendars and dependencies so you do not have to."}</p><span className={`status-pill ${riskDetected ? "status-danger" : "status-calm"}`}><i /> {riskDetected ? "AT RISK · REVIEW NOW" : "ALL SYSTEMS NOMINAL"}</span></div></div>
          </section>
          <section className="card-surface" style={{ marginTop: 20, padding: 24 }}>
            <span className="section-kicker">AUTOPILOT TALLY</span>
            <h3>{routineActionsCount} routine actions handled automatically · {humanDecisionCount} human decisions</h3>
          </section>
          <div id="settings" className="settings-anchor" aria-hidden="true" />
        </div>
      </section>
    </main>
  );
}
