"use client";

import { use, useEffect, useState } from "react";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8080";

type Commitment = {
  id: string;
  customer_name: string;
  title: string;
  scope_summary: string;
  original_deadline: string;
  committed_deadline: string;
  current_forecast: string | null;
  health: string | null;
  assessment_id: string;
  extra_cost: { amount: number };
};

type Assessment = {
  reasons: {
    title: string;
    detail: string;
    severity: string;
    evidence_ids: string[];
  }[];
  evidence: { id: string; source_name: string; source_reference: string; content: string }[];
};

type Decision = {
  id: string;
  commitment_id: string | null;
  status: string;
  reason: string;
  recommended_option_id: string | null;
  options: { id: string; title: string; summary: string; extra_cost: { amount: number } }[];
};

type Evidence = {
  id: string;
  source_name: string;
  source_reference: string;
  content: string;
  as_of: string;
};

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
  });
  if (!response.ok) throw new Error(await response.text());
  return response.json();
}

export default function CommitmentDetail({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const [commitment, setCommitment] = useState<Commitment | null>(null);
  const [assessment, setAssessment] = useState<Assessment | null>(null);
  const [decision, setDecision] = useState<Decision | null>(null);
  const [selectedEvidence, setSelectedEvidence] = useState<Evidence | null>(null);
  const [error, setError] = useState("");

  async function load() {
    const current = await request<Commitment>(`/api/commitments/${id}`);
    const [currentAssessment, decisions] = await Promise.all([
      request<Assessment>(`/api/assessments/${current.assessment_id}`),
      request<Decision[]>("/api/decisions"),
    ]);
    setCommitment(current);
    setAssessment(currentAssessment);
    setDecision(
      decisions.find(
        (item) => item.commitment_id === current.id && item.status === "OPEN",
      ) ?? null,
    );
  }

  useEffect(() => {
    load().catch((caught: unknown) => {
      setError(caught instanceof Error ? caught.message : "Could not load commitment");
    });
  }, [id]);

  async function showEvidence(evidenceId: string) {
    try {
      setSelectedEvidence(await request<Evidence>(`/api/evidence/${evidenceId}`));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not load evidence");
    }
  }

  async function approve() {
    if (!decision?.recommended_option_id) return;
    await request(`/api/decisions/${decision.id}/approve`, {
      method: "POST",
      body: JSON.stringify({ option_id: decision.recommended_option_id }),
    });
    await load();
  }

  async function reject() {
    if (!decision) return;
    await request(`/api/decisions/${decision.id}/reject`, { method: "POST" });
    await load();
  }

  if (error) return <main className="content"><div className="error-banner">⚠ {error}</div></main>;
  if (!commitment || !assessment) return <main className="content"><p>Loading commitment…</p></main>;

  const healthClass = commitment.health === "ON_TRACK" ? "status-calm" : "status-danger";
  const recommendation = decision?.options.find(
    (option) => option.id === decision.recommended_option_id,
  );

  return (
    <main className="content">
      <div className="section-heading">
        <div>
          <span className="section-kicker">COMMITMENT DETAIL</span>
          <h1>{commitment.customer_name}</h1>
          <p className="intro">{commitment.title} · {commitment.scope_summary}</p>
        </div>
        <a className="ghost-button" href="/">← Autopilot</a>
      </div>

      <section className="metric-grid">
        <div className="metric-card"><div><small>STATUS</small><strong><span className={`status-pill ${healthClass}`}><i /> {commitment.health ?? "UNKNOWN"}</span></strong></div></div>
        <div className="metric-card"><div><small>ORIGINAL COMMITMENT</small><strong>{commitment.committed_deadline}</strong></div></div>
        <div className="metric-card"><div><small>CURRENT FORECAST</small><strong>{commitment.current_forecast ?? "—"}</strong></div></div>
        <div className="metric-card"><div><small>EXTRA COST</small><strong>₹{commitment.extra_cost.amount.toLocaleString("en-IN")}</strong></div></div>
      </section>

      <section className="decision-layout">
        <article className="decision-card card-surface">
          <div className="side-card-heading"><div><span className="section-kicker">WHY</span><h2>Operating reasons</h2></div></div>
          <div className="reasons-list">
            {assessment.reasons.map((reason) => (
              <div className="reason-row" key={reason.title}>
                <div><strong>{reason.title}</strong><p>{reason.detail}</p><small>{reason.severity.toUpperCase()}</small></div>
              </div>
            ))}
          </div>
        </article>

        <aside className="options-card card-surface">
          <div className="side-card-heading"><div><span className="section-kicker">RECOMMENDATION</span><h2>{recommendation?.title ?? "No open decision"}</h2></div></div>
          <p className="intro">{decision?.reason ?? "This commitment is currently being monitored."}</p>
          {recommendation && <p className="intro">Additional cost: ₹{recommendation.extra_cost.amount.toLocaleString("en-IN")}</p>}
          {decision?.status === "OPEN" && (
            <div className="decision-footer">
              <button className="primary-button" onClick={approve}>APPROVE</button>
              <button className="ghost-button" onClick={reject}>REJECT</button>
            </div>
          )}
        </aside>
      </section>

      <section className="card-surface" style={{ marginTop: 20, padding: 24 }}>
        <div className="side-card-heading"><div><span className="section-kicker">EVIDENCE</span><h2>Sources behind this commitment</h2></div></div>
        <div className="reasons-list">
          {assessment.evidence.map((evidence) => (
            <button className="option-row" type="button" key={evidence.id} onClick={() => showEvidence(evidence.id)}>
              <div className="option-copy"><strong>{evidence.source_name}</strong><p>{evidence.source_reference}</p></div>
              <span className="option-check">OPEN</span>
            </button>
          ))}
        </div>
      </section>

      {selectedEvidence && (
        <aside className="card-surface" style={{ marginTop: 20, padding: 24 }}>
          <div className="side-card-heading"><div><span className="section-kicker">EVIDENCE SOURCE</span><h2>{selectedEvidence.source_name}</h2></div><button className="ghost-button" onClick={() => setSelectedEvidence(null)}>Close</button></div>
          <p className="intro">{selectedEvidence.content}</p>
          <small>{selectedEvidence.source_reference} · as of {selectedEvidence.as_of}</small>
        </aside>
      )}
    </main>
  );
}
