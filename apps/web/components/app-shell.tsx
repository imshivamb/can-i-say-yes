"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Activity, Globe, LayoutDashboard, ListChecks } from "lucide-react";

import { BrandMark } from "@/components/brand-mark";
import { cn } from "@/lib/utils";

const NAV = [
  { href: "/", label: "Autopilot", hint: "Decide on a promise", icon: LayoutDashboard },
  { href: "/commitments", label: "Commitments", hint: "Jobs already promised", icon: ListChecks },
  { href: "/activity", label: "Activity", hint: "What the agent just did", icon: Activity },
  { href: "/world", label: "Your world", hint: "Where the evidence comes from", icon: Globe },
] as const;

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  return (
    <div className="flex min-h-svh bg-background">
      <aside className="hidden w-60 shrink-0 flex-col border-r border-border bg-sidebar px-3 py-6 md:flex">
        <Link href="/" className="mb-8 flex items-center gap-3 px-3">
          <BrandMark />
          <span className="min-w-0">
            <span className="block text-sm font-semibold tracking-tight">Can I Say Yes?</span>
            <span className="mt-0.5 block font-mono text-[11px] text-muted-foreground">
              Northstar Creative
            </span>
          </span>
        </Link>
        <nav className="grid gap-1">
          {NAV.map((item) => {
            const active = item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);
            const Icon = item.icon;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  "rounded-lg px-3 py-2.5 transition-colors",
                  active
                    ? "bg-sidebar-accent text-sidebar-accent-foreground"
                    : "text-muted-foreground hover:bg-sidebar-accent/60 hover:text-foreground",
                )}
              >
                <span className="flex items-center gap-2 text-sm font-medium">
                  <Icon className="size-4" />
                  {item.label}
                </span>
                <span className="mt-0.5 block pl-6 text-[11px] text-muted-foreground">
                  {item.hint}
                </span>
              </Link>
            );
          })}
        </nav>
        <p className="mt-auto px-3 font-mono text-[11px] text-muted-foreground">
          Shared demo world. Reset on Autopilot before a walkthrough.
        </p>
      </aside>
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-14 items-center justify-between border-b border-border px-4 md:px-8">
          <Link href="/" className="flex min-w-0 items-center gap-2 md:hidden">
            <BrandMark className="size-7" />
            <span className="truncate text-sm font-semibold tracking-tight">Can I Say Yes?</span>
          </Link>
          <p className="hidden font-mono text-xs text-muted-foreground md:block">
            Autopilot for promises — investigate, commit, then watch
          </p>
          <span className="font-mono text-xs text-muted-foreground">Shivam</span>
        </header>
        <div className="mx-auto w-full max-w-6xl flex-1 px-4 py-8 pb-24 md:px-8 md:pb-8">{children}</div>
        <nav className="fixed inset-x-0 bottom-0 z-40 border-t border-border bg-background/95 pb-[env(safe-area-inset-bottom)] backdrop-blur md:hidden">
          <div className="grid grid-cols-4">
            {NAV.map((item) => {
              const active = item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);
              const Icon = item.icon;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={cn(
                    "flex flex-col items-center gap-1 py-2.5 text-[11px]",
                    active ? "text-foreground" : "text-muted-foreground",
                  )}
                >
                  <Icon className="size-4" />
                  {item.label === "Your world" ? "World" : item.label}
                </Link>
              );
            })}
          </div>
        </nav>
      </div>
    </div>
  );
}
