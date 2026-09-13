import Link from "next/link";

import { Button } from "@/components/ui/button";

export default function NotFound() {
  return (
    <div className="grid gap-4">
      <h1 className="text-3xl font-semibold tracking-tight">Page not found</h1>
      <div>
        <Button asChild>
          <Link href="/">Autopilot</Link>
        </Button>
      </div>
    </div>
  );
}
