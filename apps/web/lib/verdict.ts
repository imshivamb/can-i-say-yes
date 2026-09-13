export type VerdictState = "safe" | "unsafe" | "risk" | "unknown";

export function verdictState(badge: string): VerdictState {
  switch (badge.trim().toUpperCase().replace(/\s+/g, "_")) {
    case "SAFE":
    case "ON_TRACK":
      return "safe";
    case "UNSAFE":
      return "unsafe";
    case "AT_RISK":
      return "risk";
    case "UNKNOWN":
      return "unknown";
    default:
      return "unknown";
  }
}

export function verdictLabel(badge: string): string {
  const state = verdictState(badge);
  switch (state) {
    case "safe":
      return badge.toUpperCase().includes("TRACK") ? "ON TRACK" : "SAFE TO COMMIT";
    case "unsafe":
      return "NOT SAFE TO COMMIT";
    case "risk":
      return "COMMITMENT AT RISK";
    case "unknown":
      return "UNKNOWN";
    default: {
      const _exhaustive: never = state;
      return _exhaustive;
    }
  }
}

export function severityState(severity?: string): Exclude<VerdictState, "safe"> {
  switch ((severity ?? "").toLowerCase()) {
    case "high":
      return "unsafe";
    case "medium":
      return "risk";
    default:
      return "unknown";
  }
}

export function bannerClass(state: VerdictState): string {
  switch (state) {
    case "safe":
      return "border-safe bg-safe/10 text-safe-foreground";
    case "unsafe":
      return "border-unsafe bg-unsafe/10 text-unsafe-foreground";
    case "risk":
      return "border-risk bg-risk/10 text-risk-foreground";
    case "unknown":
      return "border-unknown bg-unknown/10 text-unknown-foreground";
    default: {
      const _exhaustive: never = state;
      return _exhaustive;
    }
  }
}

export function accentClass(state: VerdictState): string {
  switch (state) {
    case "safe":
      return "bg-safe";
    case "unsafe":
      return "bg-unsafe";
    case "risk":
      return "bg-risk";
    case "unknown":
      return "bg-unknown";
    default: {
      const _exhaustive: never = state;
      return _exhaustive;
    }
  }
}
