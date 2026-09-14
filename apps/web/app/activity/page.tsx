"use client";

import { useEffect, useState } from "react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { type ActivityRecord, formatDate, request } from "@/lib/api";

export default function ActivityPage() {
  const [items, setItems] = useState<ActivityRecord[] | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    request<ActivityRecord[]>("/api/activity")
      .then(setItems)
      .catch((caught: unknown) => {
        setError(caught instanceof Error ? caught.message : "Could not load activity");
      });
  }, []);

  return (
    <div className="grid gap-6">
      <div>
        <h1 className="text-3xl font-semibold tracking-tight">Activity</h1>
        <p className="mt-2 max-w-2xl text-sm text-muted-foreground">
          What the Investigator and Monitor wrote during this demo.
        </p>
      </div>
      {error && (
        <Alert variant="destructive">
          <AlertTitle>Could not load</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}
      <Card>
        <CardHeader>
          <CardTitle>Agent log</CardTitle>
          <CardDescription>Newest first.</CardDescription>
        </CardHeader>
        <CardContent>
          {items === null ? (
            <Skeleton className="h-24 w-full" />
          ) : items.length === 0 ? (
            <p className="text-sm text-muted-foreground">No events yet. Run a check on Autopilot.</p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-28 md:w-40">When</TableHead>
                  <TableHead>Event</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {[...items].reverse().map((item, index) => (
                  <TableRow key={item.id ?? `${item.text}-${index}`}>
                    <TableCell className="font-mono text-xs text-muted-foreground">
                      {formatDate(item.timestamp)}
                    </TableCell>
                    <TableCell className="whitespace-normal">{item.text}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
