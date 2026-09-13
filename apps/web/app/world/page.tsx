"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { SourcePill } from "@/components/source-pill";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { request } from "@/lib/api";

type Source = {
  key: string;
  label: string;
  mode: "seed" | "live";
  detail: string;
  count: number | null;
};

export default function WorldPage() {
  const [sources, setSources] = useState<Source[]>([]);
  const [error, setError] = useState("");
  const [pollNote, setPollNote] = useState("");
  const [busy, setBusy] = useState(false);

  async function load() {
    setSources(await request<Source[]>("/api/world/sources"));
  }

  useEffect(() => {
    load().catch((caught: unknown) => {
      setError(caught instanceof Error ? caught.message : "Could not load sources");
    });
  }, []);

  async function pollInbox() {
    setBusy(true);
    setError("");
    try {
      const result = await request<{ new_events: number; new_requests: number }>(
        "/api/integrations/gmail/poll",
        { method: "POST" },
      );
      setPollNote(`${result.new_requests} new requests · ${result.new_events} events`);
      await load();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Poll failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="grid gap-8">
      <div>
        <h1 className="text-3xl font-semibold tracking-tight">Your world</h1>
        <p className="mt-2 max-w-2xl text-sm text-muted-foreground">
          Where the evidence comes from. On the public demo every source is seed JSON. That is
          honest.
        </p>
      </div>

      {error && (
        <Alert variant="destructive">
          <AlertTitle>Something failed</AlertTitle>
          <AlertDescription className="font-mono text-xs">{error}</AlertDescription>
        </Alert>
      )}

      <Card>
        <CardHeader className="flex flex-row flex-wrap items-start justify-between gap-4">
          <div>
            <CardTitle>Sources</CardTitle>
            <CardDescription>Seed files, or live calendar and inbox when tokens are set.</CardDescription>
          </div>
          <Button onClick={pollInbox} disabled={busy} size="sm">
            {busy ? "Polling…" : "Poll inbox"}
          </Button>
        </CardHeader>
        <CardContent className="grid gap-3">
          {pollNote && <p className="font-mono text-xs text-muted-foreground">{pollNote}</p>}
          {sources.map((source) => (
            <div
              key={source.key}
              className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-border px-3 py-3"
            >
              <div>
                <p className="text-sm font-medium">{source.label}</p>
                <p className="font-mono text-xs text-muted-foreground">{source.detail}</p>
              </div>
              <div className="flex items-center gap-3">
                {source.count !== null && (
                  <span className="font-mono text-xs text-muted-foreground">{source.count}</span>
                )}
                <SourcePill mode={source.mode} />
              </div>
            </div>
          ))}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Run it on your own operation</CardTitle>
          <CardDescription>
            The seed world is plain JSON. Point the agent at yours, then press Reset on Autopilot.
          </CardDescription>
        </CardHeader>
        <CardContent className="grid gap-2 text-sm text-muted-foreground">
          <p>1. Copy `data/` and replace the files under company, projects, suppliers, emails, documents.</p>
          <p>2. Set `CISAY_DATA_DIR` to that folder.</p>
          <p>3. Optional: `CISAY_LIVE_INTEGRATIONS=1` plus a Google token. Calendar and Inbox flip to Live.</p>
          <p>
            Back to{" "}
            <Link href="/" className="underline underline-offset-4">
              Autopilot
            </Link>
            .
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
