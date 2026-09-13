import { cn } from "@/lib/utils";

export function SourcePill({ mode }: { mode: "seed" | "live" }) {
  const live = mode === "live";
  return (
    <span
      className={cn(
        "rounded-full px-2 py-0.5 font-mono text-[11px]",
        live ? "bg-safe/15 text-safe" : "bg-unknown/15 text-unknown",
      )}
    >
      {live ? "Live" : "Seed"}
    </span>
  );
}
