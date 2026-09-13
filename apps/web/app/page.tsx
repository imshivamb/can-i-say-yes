"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import {
  type Assessment,
  type Clock,
  type Commitment,
  type Decision,
  RECORDED,
  healthLabel,
  money,
  request,
  requestJob,
} from "@/lib/api";

type ExampleKey = "acme" | "nova";
const EXAMPLES: Record<
  ExampleKey,
  { customer: string; request: string; date: string; budget: string; scope: string }
> = {
  acme: {
    customer: "Acme Foods",
    request:
      "We'd like 12 social creatives, a landing page and three short videos for our September campaign. Can you have everything ready by September 18 for ₹4.2 lakh?",
    date: "18 September",
    budget: "₹4,20,000",
    scope: "12 creatives, 1 landing page, 3 videos",
  },
  nova: {
    customer: "Nova Health",
    request: "Can Northstar build our product launch site with six pages by October 9 for ₹5.2 lakh?",
    date: "09 October",
    budget: "₹5,20,000",
    scope: "6-page launch site",
  },
};

type Phase = "idle" | "working" | "decide" | "watching" | "at_risk" | "done";
type WorkKind = "investigate" | "approve" | "supplier" | "fix" | "reset" | "clock";

export default function AutopilotPage() {
  const [assessment, setAssessment] = useState<Assessment | null>(null);
  const [decision, setDecision] = useState<Decision | null>(null);
  const [commitments, setCommitments] = useState<Commitment[]>([]);
  const [openCount, setOpenCount] = useState(0);
  const [clock, setClock] = useState<Clock | null>(null);
  const [approved, setApproved] = useState(false);
  const [riskDecision, setRiskDecision] = useState<Decision | null>(null);
  const [riskCommitment, setRiskCommitment] = useState<Commitment | null>(null);
  const [riskApproved, setRiskApproved] = useState(false);
  const [selectedOption, setSelectedOption] = useState<string | null>(null);
  const [example, setExample] = useState<ExampleKey>("acme");
  const [error, setError] = useState("");
  const [work, setWork] = useState<WorkKind | null>(null);

  const busy = work !== null;
  const current = EXAMPLES[example];

  async function refresh() {
    const [commitmentItems, decisionItems, clockItem] = await Promise.all([
      request<Commitment[]>("/api/commitments"),
      request<Decision[]>("/api/decisions"),
      request<Clock>("/api/clock"),
    ]);
    setCommitments(commitmentItems);
    setOpenCount(decisionItems.filter((item) => item.status === "OPEN").length);
    setClock(clockItem);
  }

  async function loadRisk() {
    const [openDecisions, currentCommitments] = await Promise.all([
      request<Decision[]>("/api/decisions"),
      request<Commitment[]>("/api/commitments"),
    ]);
    const opened = openDecisions.find((item) => item.status === "OPEN" && item.commitment_id);
    setRiskDecision(opened ?? null);
    setRiskCommitment(
      opened ? (currentCommitments.find((item) => item.id === opened.commitment_id) ?? null) : null,
    );
    setSelectedOption(opened?.recommended_option_id ?? null);
  }

  useEffect(() => {
    refresh().catch(() => undefined);
  }, []);

  const phase: Phase = (() => {
    if (work === "investigate") return "working";
    if (riskApproved) return "done";
    if (riskDecision) return "at_risk";
    if (approved) return "watching";
    if (assessment && decision && !approved) return "decide";
    return "idle";
  })();

  async function assess() {
    setWork("investigate");
    setError("");
    try {
      const created = await requestJob<{ request: { id: string } }>("/api/requests", {
        method: "POST",
        body: JSON.stringify({ text: current.request, recorded: RECORDED, example }),
      });
      const result = await requestJob<{ assessment: Assessment; decision: Decision }>(
        `/api/requests/${created.request.id}/assess?recorded=${RECORDED}`,
        { method: "POST" },
      );
      setAssessment(result.assessment);
      setDecision(result.decision);
      setSelectedOption(
        result.decision.recommended_option_id ?? result.assessment.alternatives[0]?.id ?? null,
      );
      await refresh();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Investigation failed");
    } finally {
      setWork(null);
    }
  }

  async function approve() {
    if (!decision) return;
    setWork("approve");
    setError("");
    try {
      await request(`/api/decisions/${decision.id}/approve`, {
        method: "POST",
        body: JSON.stringify({
          option_id: selectedOption ?? decision.recommended_option_id ?? "alt_a",
        }),
      });
      setApproved(true);
      await refresh();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Approval failed");
    } finally {
      setWork(null);
    }
  }

  async function sendSupplier() {
    setWork("supplier");
    setError("");
    try {
      await requestJob<{ opened_decisions: number }>("/api/events/inbound", {
        method: "POST",
        body: JSON.stringify({
          event_id: `evt_demo_${Date.now()}`,
          summary: "Frame & Grain: editor availability slipped to September 20",
          source_reference: "gmail:demo-supplier-delay",
          payload: { supplier_id: "sup_frame_grain", available_from: "2026-09-20" },
        }),
      });
      await refresh();
      await loadRisk();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Supplier update failed");
    } finally {
      setWork(null);
    }
  }

  async function approveRisk() {
    if (!riskDecision || !selectedOption) return;
    setWork("fix");
    setError("");
    try {
      await request(`/api/decisions/${riskDecision.id}/approve`, {
        method: "POST",
        body: JSON.stringify({ option_id: selectedOption }),
      });
      setRiskApproved(true);
      setRiskDecision(null);
      await refresh();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not approve the fix");
    } finally {
      setWork(null);
    }
  }

  async function resetDemo() {
    setWork("reset");
    setError("");
    try {
      await request("/api/demo/reset", { method: "POST" });
      setAssessment(null);
      setDecision(null);
      setApproved(false);
      setRiskDecision(null);
      setRiskCommitment(null);
      setRiskApproved(false);
      setSelectedOption(null);
      await refresh();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not reset");
    } finally {
      setWork(null);
    }
  }

  async function advanceTime() {
    setWork("clock");
    try {
      await requestJob("/api/clock/advance", {
        method: "POST",
        body: JSON.stringify({ to: "supplier_delay", recorded: RECORDED }),
      });
      await refresh();
      await loadRisk();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not advance time");
    } finally {
      setWork(null);
    }
  }

  const onTrack = commitments.filter((item) => item.health === "ON_TRACK").length;
  const atRisk = commitments.filter((item) => item.health === "AT_RISK").length;
  const clockDate = clock ? new Date(clock.now) : null;
  const options = riskDecision?.options ?? assessment?.alternatives ?? [];
  const selected = options.find((item) => item.id === selectedOption);
  const liveCommitment = commitments.find((item) => item.customer_name === current.customer);

  return (
    <div className="grid gap-8">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="font-mono text-xs text-muted-foreground">
            {clockDate
              ? clockDate.toLocaleString("en-IN", {
                  weekday: "long",
                  day: "numeric",
                  month: "long",
                  year: "numeric",
                  hour: "numeric",
                  minute: "2-digit",
                })
              : "Loading studio clock…"}
          </p>
          <h1 className="mt-2 text-3xl font-semibold tracking-tight">Good morning, Shivam.</h1>
          <p className="mt-2 max-w-xl text-sm text-muted-foreground">
            Before Northstar promises a date, the Investigator checks capacity, calendars, and
            suppliers. After you commit, the Monitor watches for slips.
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={advanceTime} disabled={busy}>
            Advance clock
          </Button>
          <Button variant="outline" size="sm" onClick={resetDemo} disabled={busy}>
            Reset demo
          </Button>
        </div>
      </div>

      <NowCard
        phase={phase}
        work={work}
        customer={current.customer}
        selectedTitle={selected?.title}
        onAssess={assess}
        onApprove={approve}
        onSupplier={sendSupplier}
        onFix={approveRisk}
        onSwitchExample={() => setExample(example === "acme" ? "nova" : "acme")}
        otherExample={example === "acme" ? "Nova Health" : "Acme Foods"}
        busy={busy}
      />

      {error && (
        <Alert variant="destructive">
          <AlertTitle>Something failed</AlertTitle>
          <AlertDescription className="font-mono text-xs">{error}</AlertDescription>
        </Alert>
      )}

      <section className="grid gap-3 sm:grid-cols-4">
        <Stat label="Commitments" value={commitments.length} hint="Jobs already promised" />
        <Stat label="On track" value={onTrack} hint="Forecast matches the promise" />
        <Stat label="At risk" value={atRisk} hint="Forecast slipped past the promise" />
        <Stat label="Needs you" value={openCount} hint="Open decisions only" />
      </section>

      {phase === "working" && (
        <Card>
          <CardHeader>
            <CardTitle>Investigator is working</CardTitle>
            <CardDescription>
              Checking remaining hours, existing jobs, supplier windows, and the requested date.
              This usually takes 20–45 seconds.
            </CardDescription>
          </CardHeader>
          <CardContent className="grid gap-3">
            <Skeleton className="h-4 w-2/3" />
            <Skeleton className="h-4 w-1/2" />
            <Skeleton className="h-4 w-3/5" />
          </CardContent>
        </Card>
      )}

      {phase === "idle" && (
        <Card>
          <CardHeader>
            <CardTitle>Incoming request</CardTitle>
            <CardDescription>{current.customer} asked if Northstar can take this work.</CardDescription>
          </CardHeader>
          <CardContent className="grid gap-3 text-sm">
            <p className="max-w-2xl text-muted-foreground">{current.request}</p>
            <div className="flex flex-wrap gap-2 font-mono text-xs text-muted-foreground">
              <span>Due {current.date}</span>
              <span>·</span>
              <span>{current.budget}</span>
              <span>·</span>
              <span>{current.scope}</span>
            </div>
          </CardContent>
        </Card>
      )}

      {(phase === "decide" || phase === "watching") && assessment && (
        <DecisionPanel
          title={
            phase === "watching"
              ? "Promise is live. The Monitor is watching it."
              : assessment.decision === "SAFE"
                ? "This date can be kept — if you accept the recommended option."
                : "The requested date is unsafe."
          }
          badge={assessment.decision}
          facts={[
            ["Requested", current.date],
            ["Budget", current.budget],
            ["Confidence", `${Math.round((assessment.confidence ?? 0) * 100)}%`],
          ]}
          reasons={assessment.reasons}
          options={assessment.alternatives}
          selectedId={selectedOption}
          onSelect={setSelectedOption}
          locked={phase !== "decide" || busy}
        />
      )}

      {phase === "at_risk" && riskDecision && (
        <DecisionPanel
          title="A supplier slipped. The committed date may miss."
          badge="AT RISK"
          facts={[
            ["Committed", riskCommitment?.committed_deadline ?? "—"],
            ["New forecast", riskCommitment?.current_forecast ?? "—"],
            ["Health", healthLabel(riskCommitment?.health)],
          ]}
          reasons={[{ title: "Supplier delay", detail: riskDecision.reason, evidence_ids: [] }]}
          options={riskDecision.options ?? []}
          selectedId={selectedOption}
          onSelect={setSelectedOption}
          locked={busy}
        />
      )}

      {phase === "done" && (
        <Alert>
          <AlertTitle>Backup approved. Nothing is waiting on you.</AlertTitle>
          <AlertDescription>
            The Monitor caught the slip and you chose a fix. Reset demo to walk the loop again.
          </AlertDescription>
        </Alert>
      )}

      {liveCommitment && (phase === "watching" || phase === "at_risk" || phase === "done") && (
        <p className="text-sm text-muted-foreground">
          Open{" "}
          <Link href={`/commitments/${liveCommitment.id}`} className="underline underline-offset-4">
            {liveCommitment.customer_name}
          </Link>{" "}
          or the{" "}
          <Link href="/activity" className="underline underline-offset-4">
            activity log
          </Link>
          .
        </p>
      )}
    </div>
  );
}

function Stat({ label, value, hint }: { label: string; value: number; hint: string }) {
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardDescription>{label}</CardDescription>
        <CardTitle className="font-mono text-3xl tabular-nums">{value}</CardTitle>
      </CardHeader>
      <CardContent className="text-xs text-muted-foreground">{hint}</CardContent>
    </Card>
  );
}

function NowCard({
  phase,
  work,
  customer,
  selectedTitle,
  onAssess,
  onApprove,
  onSupplier,
  onFix,
  onSwitchExample,
  otherExample,
  busy,
}: {
  phase: Phase;
  work: WorkKind | null;
  customer: string;
  selectedTitle?: string;
  onAssess: () => void;
  onApprove: () => void;
  onSupplier: () => void;
  onFix: () => void;
  onSwitchExample: () => void;
  otherExample: string;
  busy: boolean;
}) {
  const copy = nowCopy(phase, work, customer, selectedTitle);
  return (
    <Card className="border-primary/20">
      <CardHeader className="flex flex-row flex-wrap items-start justify-between gap-4">
        <div className="max-w-xl">
          <p className="font-mono text-xs text-muted-foreground">Now</p>
          <CardTitle className="mt-1 text-xl">{copy.title}</CardTitle>
          <CardDescription className="mt-2 text-sm">{copy.body}</CardDescription>
        </div>
        <div className="flex flex-wrap gap-2">
          {phase === "idle" && (
            <>
              <Button onClick={onAssess} disabled={busy}>
                Check feasibility
              </Button>
              <Button variant="ghost" onClick={onSwitchExample} disabled={busy}>
                Use {otherExample} instead
              </Button>
            </>
          )}
          {phase === "decide" && (
            <Button onClick={onApprove} disabled={busy}>
              {work === "approve" ? "Saving promise…" : `Approve ${selectedTitle ?? "selected option"}`}
            </Button>
          )}
          {phase === "watching" && (
            <Button onClick={onSupplier} disabled={busy}>
              {work === "supplier" ? "Monitor is re-checking…" : "Simulate supplier delay"}
            </Button>
          )}
          {phase === "at_risk" && (
            <Button onClick={onFix} disabled={busy}>
              {work === "fix" ? "Saving fix…" : `Approve ${selectedTitle ?? "selected option"}`}
            </Button>
          )}
        </div>
      </CardHeader>
    </Card>
  );
}

function nowCopy(
  phase: Phase,
  work: WorkKind | null,
  customer: string,
  selectedTitle?: string,
): { title: string; body: string } {
  if (work === "investigate") {
    return {
      title: `Investigator is checking ${customer}`,
      body: "Reading capacity, existing commitments, calendars, and supplier windows.",
    };
  }
  if (work === "supplier") {
    return {
      title: "Monitor received a supplier email",
      body: "Frame & Grain slipped. The agent is re-evaluating the promise.",
    };
  }
  switch (phase) {
    case "idle":
      return {
        title: `${customer} asked if you can say yes`,
        body: "Run the Investigator. A commitment is created only after you approve.",
      };
    case "working":
      return {
        title: "Investigator is still working",
        body: "Stay on this page. The finding usually takes 20–45 seconds.",
      };
    case "decide":
      return {
        title: "Pick the promise",
        body: `${selectedTitle ?? "An option"} is selected. Approving writes it into the live book.`,
      };
    case "watching":
      return {
        title: "Committed. Next, prove the Monitor",
        body: "Simulate the Frame & Grain delay to see the agent reopen a decision.",
      };
    case "at_risk":
      return {
        title: "Protect the delivery",
        body: "Approve a fix or the date stays at risk. The Monitor will not change the plan alone.",
      };
    case "done":
      return {
        title: "Loop complete",
        body: "Investigate → commit → world changes → Monitor asks → you fix.",
      };
    default: {
      const _exhaustive: never = phase;
      return _exhaustive;
    }
  }
}

function DecisionPanel({
  title,
  badge,
  facts,
  reasons,
  options,
  selectedId,
  onSelect,
  locked,
}: {
  title: string;
  badge: string;
  facts: [string, string][];
  reasons: { title: string; detail: string; evidence_ids: string[] }[];
  options: { id: string; title: string; summary: string; extra_cost: { amount: number }; recommended?: boolean }[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  locked: boolean;
}) {
  return (
    <div className="grid gap-4 lg:grid-cols-[1.3fr_1fr]">
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between gap-3">
            <CardTitle className="text-lg">{title}</CardTitle>
            <Badge variant={badge === "SAFE" || badge === "ON TRACK" ? "secondary" : "destructive"}>
              {badge}
            </Badge>
          </div>
        </CardHeader>
        <CardContent className="grid gap-6">
          <div className="grid grid-cols-3 gap-4">
            {facts.map(([label, value]) => (
              <div key={label}>
                <p className="font-mono text-[11px] text-muted-foreground">{label}</p>
                <p className="mt-1 text-sm font-medium">{value}</p>
              </div>
            ))}
          </div>
          <Separator />
          <div className="grid gap-3">
            {reasons.slice(0, 4).map((reason) => (
              <div key={reason.title}>
                <p className="text-sm font-medium">{reason.title}</p>
                <p className="text-sm text-muted-foreground">{reason.detail}</p>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Your options</CardTitle>
          <CardDescription>One is recommended. You still choose.</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-2">
          {options.map((option) => {
            const active = option.id === selectedId;
            return (
              <button
                key={option.id}
                type="button"
                disabled={locked}
                onClick={() => onSelect(option.id)}
                className={`rounded-lg border px-3 py-3 text-left transition-colors ${
                  active ? "border-primary bg-accent" : "border-border hover:bg-muted/40"
                }`}
              >
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="text-sm font-medium">{option.title}</p>
                    <p className="mt-1 text-xs text-muted-foreground">{option.summary}</p>
                  </div>
                  <span className="font-mono text-xs text-muted-foreground">
                    {money(option.extra_cost.amount)}
                  </span>
                </div>
                {option.recommended && (
                  <p className="mt-2 font-mono text-[11px] text-muted-foreground">Recommended</p>
                )}
              </button>
            );
          })}
        </CardContent>
      </Card>
    </div>
  );
}
