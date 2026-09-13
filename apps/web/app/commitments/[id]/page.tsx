"use client";

import Link from "next/link";
import { use, useEffect, useState } from "react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import {
  type Assessment,
  type Commitment,
  type Decision,
  formatDate,
  healthLabel,
  money,
  request,
} from "@/lib/api";

type Evidence = {
  id: string;
  source_name: string;
  source_reference: string;
  content: string;
  as_of: string;
};

export default function CommitmentDetail({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const [commitment, setCommitment] = useState<Commitment | null>(null);
  const [assessment, setAssessment] = useState<Assessment | null>(null);
  const [decision, setDecision] = useState<Decision | null>(null);
  const [selectedEvidence, setSelectedEvidence] = useState<Evidence | null>(null);
  const [error, setError] = useState("");

  async function load() {
    const current = await request<Commitment>(`/api/commitments/${id}`);
    const decisions = await request<Decision[]>("/api/decisions");
    let currentAssessment: Assessment | null = null;
    if (current.assessment_id) {
      try {
        currentAssessment = await request<Assessment>(`/api/assessments/${current.assessment_id}`);
      } catch {
        currentAssessment = null;
      }
    }
    setCommitment(current);
    setAssessment(currentAssessment);
    setDecision(
      decisions.find((item) => item.commitment_id === current.id && item.status === "OPEN") ?? null,
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

  if (error) {
    return (
      <Alert variant="destructive">
        <AlertTitle>Could not load</AlertTitle>
        <AlertDescription>{error}</AlertDescription>
      </Alert>
    );
  }
  if (!commitment) {
    return (
      <div className="grid gap-3">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-40 w-full" />
      </div>
    );
  }

  const recommendation = decision?.options?.find((option) => option.id === decision.recommended_option_id);

  return (
    <div className="grid gap-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="font-mono text-xs text-muted-foreground">
            <Link href="/commitments" className="hover:underline">
              Commitments
            </Link>
            {" / "}
            {commitment.id}
          </p>
          <h1 className="mt-2 text-3xl font-semibold tracking-tight">{commitment.customer_name}</h1>
          <p className="mt-2 text-sm text-muted-foreground">{commitment.title}</p>
        </div>
        <Badge variant={commitment.health === "AT_RISK" ? "destructive" : "secondary"}>
          {healthLabel(commitment.health)}
        </Badge>
      </div>

      <div className="grid gap-3 sm:grid-cols-3">
        <Card>
          <CardHeader>
            <CardDescription>Committed</CardDescription>
            <CardTitle className="font-mono text-lg">{formatDate(commitment.committed_deadline)}</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader>
            <CardDescription>Forecast</CardDescription>
            <CardTitle className="font-mono text-lg">{formatDate(commitment.current_forecast)}</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader>
            <CardDescription>Extra cost</CardDescription>
            <CardTitle className="font-mono text-lg">
              {money(commitment.extra_cost?.amount ?? 0)}
            </CardTitle>
          </CardHeader>
        </Card>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Assessment</CardTitle>
          </CardHeader>
          <CardContent className="grid gap-4">
            {assessment ? (
              assessment.reasons.map((reason) => (
                <div key={reason.title}>
                  <p className="text-sm font-medium">{reason.title}</p>
                  <p className="text-sm text-muted-foreground">{reason.detail}</p>
                </div>
              ))
            ) : (
              <p className="text-sm text-muted-foreground">No assessment on file.</p>
            )}
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Decision</CardTitle>
            {decision && <CardDescription>{decision.reason}</CardDescription>}
          </CardHeader>
          <CardContent className="grid gap-3">
            {recommendation && (
              <p className="text-sm">
                Recommended: <span className="font-medium">{recommendation.title}</span>{" "}
                <span className="text-muted-foreground">({money(recommendation.extra_cost.amount)})</span>
              </p>
            )}
            {decision?.status === "OPEN" && (
              <div className="flex gap-2">
                <Button onClick={approve}>Approve</Button>
                <Button variant="outline" onClick={reject}>
                  Reject
                </Button>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Evidence</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-2">
          {(assessment?.evidence ?? []).length === 0 ? (
            <p className="text-sm text-muted-foreground">None cited.</p>
          ) : (
            (assessment?.evidence ?? []).map((evidence) => (
              <button
                key={evidence.id}
                type="button"
                className="rounded-lg border border-border px-3 py-2 text-left hover:bg-muted/40"
                onClick={() => showEvidence(evidence.id)}
              >
                <p className="text-sm font-medium">{evidence.source_name}</p>
                <p className="font-mono text-xs text-muted-foreground">{evidence.source_reference}</p>
              </button>
            ))
          )}
        </CardContent>
      </Card>

      {selectedEvidence && (
        <Card>
          <CardHeader className="flex flex-row items-start justify-between">
            <div>
              <CardTitle>{selectedEvidence.source_name}</CardTitle>
              <CardDescription className="font-mono">
                {selectedEvidence.source_reference} · {selectedEvidence.as_of}
              </CardDescription>
            </div>
            <Button variant="ghost" size="sm" onClick={() => setSelectedEvidence(null)}>
              Close
            </Button>
          </CardHeader>
          <Separator />
          <CardContent className="pt-6">
            <p className="text-sm text-muted-foreground">{selectedEvidence.content}</p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
