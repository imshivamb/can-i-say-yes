export const API = process.env.NEXT_PUBLIC_API_URL ?? "";
export const RECORDED = process.env.NEXT_PUBLIC_RECORDED === "1";

export type Assessment = {
  decision: string;
  confidence?: number;
  reasons: { title: string; detail: string; evidence_ids: string[]; severity?: string }[];
  alternatives: {
    id: string;
    title: string;
    summary: string;
    extra_cost: { amount: number };
    recommended?: boolean;
  }[];
  evidence?: { id: string; source_name: string; source_reference: string; content: string }[];
};

export type Decision = {
  id: string;
  commitment_id?: string | null;
  request_id?: string;
  status?: string;
  recommended_option_id?: string | null;
  reason: string;
  options?: { id: string; title: string; summary: string; extra_cost: { amount: number } }[];
};

export type Commitment = {
  id: string;
  customer_name: string;
  title: string;
  scope_summary?: string;
  request_id?: string;
  health?: string | null;
  status?: string;
  committed_deadline?: string;
  current_forecast?: string | null;
  assessment_id?: string;
  extra_cost?: { amount: number };
};

export type Clock = { now: string };
export type ActivityRecord = {
  id?: string;
  text: string;
  timestamp?: string;
  commitment_id?: string | null;
};

export async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
  });
  if (!response.ok) throw new Error(await response.text());
  return response.json();
}

type JobStatus = "pending" | "done" | "error";

function assertNever(value: never): never {
  throw new Error(`unhandled job status: ${String(value)}`);
}

export async function requestJob<T>(path: string, init?: RequestInit): Promise<T> {
  const joined = path.includes("?") ? `${path}&async_job=true` : `${path}?async_job=true`;
  const started = await request<{ job_id?: string; status?: string }>(joined, init);
  if (started.status !== "pending" || !started.job_id) {
    return started as T;
  }
  const deadline = Date.now() + 180_000;
  while (Date.now() < deadline) {
    await new Promise((resolve) => setTimeout(resolve, 1000));
    const job = await request<{ status: JobStatus; result?: T; detail?: string }>(
      `/api/jobs/${started.job_id}`,
    );
    switch (job.status) {
      case "pending":
        break;
      case "done":
        if (!job.result) throw new Error("Job completed without a result");
        return job.result;
      case "error":
        throw new Error(job.detail ?? "Job failed");
      default:
        return assertNever(job.status);
    }
  }
  throw new Error("Timed out waiting for the agent. Press Reset and try again.");
}

export function money(amount: number): string {
  return amount === 0 ? "₹0" : `₹${amount.toLocaleString("en-IN")}`;
}

export function healthLabel(health: string | null | undefined): string {
  switch (health) {
    case "ON_TRACK":
      return "On track";
    case "AT_RISK":
      return "At risk";
    case "UNKNOWN":
      return "Unknown";
    default:
      return health ?? "—";
  }
}

export function formatDate(value: string | null | undefined): string {
  if (!value) return "—";
  if (/^\d{4}-\d{2}-\d{2}$/.test(value)) {
    const [year, month, day] = value.split("-").map(Number);
    return new Date(year, month - 1, day).toLocaleDateString("en-IN", {
      day: "numeric",
      month: "short",
      year: "numeric",
    });
  }
  return new Date(value).toLocaleString("en-IN", {
    day: "numeric",
    month: "short",
    hour: "numeric",
    minute: "2-digit",
  });
}
