import Link from "next/link";

import { SeverityDot } from "@/components/severity-dot";
import { bannerClass, verdictLabel, verdictState } from "@/lib/verdict";
import { cn } from "@/lib/utils";

type Reason = {
  title: string;
  detail: string;
  evidence_ids: string[];
  severity?: string;
};

export function VerdictBanner({
  badge,
  facts,
  reasons,
  evidenceHref,
}: {
  badge: string;
  facts: [string, string][];
  reasons: Reason[];
  evidenceHref?: string;
}) {
  const state = verdictState(badge);
  return (
    <div className={cn("rounded-lg border-l-4 px-5 py-4", bannerClass(state))}>
      <div className="flex flex-wrap items-start justify-between gap-4">
        <p className="text-[28px] font-semibold leading-none tracking-tight">
          {verdictLabel(badge)}
        </p>
        <div className="flex flex-wrap gap-6 font-mono text-xs">
          {facts.map(([label, value]) => (
            <div key={label}>
              <p className="text-muted-foreground">{label}</p>
              <p className="mt-1 text-sm text-foreground">{value}</p>
            </div>
          ))}
        </div>
      </div>
      <div className="mt-5 grid gap-3">
        {reasons.slice(0, 4).map((reason) => (
          <div key={reason.title} className="flex items-start gap-3">
            <SeverityDot severity={reason.severity} />
            <div className="min-w-0">
              <p className="text-sm font-medium text-foreground">{reason.title}</p>
              <p className="text-sm text-muted-foreground">{reason.detail}</p>
              {reason.evidence_ids.length > 0 && (
                <div className="mt-2 flex flex-wrap gap-1.5">
                  {reason.evidence_ids.map((id) => {
                    const chip = (
                      <span className="rounded-md bg-background/50 px-1.5 py-0.5 font-mono text-[11px] text-muted-foreground">
                        {id}
                      </span>
                    );
                    return evidenceHref ? (
                      <Link key={id} href={evidenceHref} className="hover:text-foreground">
                        {chip}
                      </Link>
                    ) : (
                      <span key={id}>{chip}</span>
                    );
                  })}
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
