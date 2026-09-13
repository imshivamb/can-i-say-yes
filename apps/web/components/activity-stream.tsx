"use client";

import { useEffect, useRef } from "react";

import type { ActivityRecord } from "@/lib/api";

function toolName(text: string): string {
  return text.split(" ")[0] ?? text;
}

function statusLabel(text: string): string {
  if (text.includes("blocked")) return "blocked";
  if (text.includes("completed")) return "completed";
  if (text.includes("started")) return "started";
  return "update";
}

export function ActivityStream({
  items,
  busy,
  elapsedSeconds,
}: {
  items: ActivityRecord[];
  busy: boolean;
  elapsedSeconds: number;
}) {
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ block: "nearest" });
  }, [items.length]);

  if (!busy && items.length > 0) {
    return (
      <p className="font-mono text-xs text-muted-foreground">
        {items.length} tool calls · {elapsedSeconds}s
      </p>
    );
  }

  if (!busy) return null;

  return (
    <div className="max-h-48 overflow-y-auto rounded-md border border-border bg-background/40 px-3 py-2">
      {items.length === 0 && (
        <p className="font-mono text-xs text-muted-foreground">Waiting for the first tool call…</p>
      )}
      <ul className="grid gap-1.5">
        {items.map((item) => (
          <li
            key={item.id ?? `${item.text}-${item.timestamp}`}
            className="flex items-center gap-2 font-mono text-xs"
            style={{ animation: "activity-in 160ms ease-out" }}
          >
            <span className="size-2 shrink-0 rounded-full bg-agent animate-pulse" />
            <span className="text-foreground">{toolName(item.text)}</span>
            <span className="text-muted-foreground">{statusLabel(item.text)}</span>
          </li>
        ))}
      </ul>
      <div ref={endRef} />
    </div>
  );
}
