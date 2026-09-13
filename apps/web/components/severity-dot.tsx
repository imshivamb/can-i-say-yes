import { accentClass, severityState } from "@/lib/verdict";
import { cn } from "@/lib/utils";

export function SeverityDot({ severity }: { severity?: string }) {
  const state = severityState(severity);
  return (
    <span
      aria-hidden
      className={cn("mt-1.5 size-2 shrink-0 rounded-full", accentClass(state))}
    />
  );
}
