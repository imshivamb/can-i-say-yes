"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
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
import { type Commitment, formatDate, healthLabel, request } from "@/lib/api";

export default function CommitmentsPage() {
  const router = useRouter();
  const [items, setItems] = useState<Commitment[] | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    request<Commitment[]>("/api/commitments")
      .then(setItems)
      .catch((caught: unknown) => {
        setError(caught instanceof Error ? caught.message : "Could not load commitments");
      });
  }, []);

  return (
    <div className="grid gap-6">
      <div>
        <h1 className="text-3xl font-semibold tracking-tight">Commitments</h1>
        <p className="mt-2 max-w-2xl text-sm text-muted-foreground">
          Every job Northstar has already promised. Health is forecast versus the committed date.
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
          <CardTitle>Live book</CardTitle>
          <CardDescription>
            Click a row for dates, assessment, and any open decision.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {items === null ? (
            <div className="grid gap-2">
              <Skeleton className="h-10 w-full" />
              <Skeleton className="h-10 w-full" />
              <Skeleton className="h-10 w-full" />
            </div>
          ) : items.length === 0 ? (
            <p className="text-sm text-muted-foreground">No promises yet.</p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Customer</TableHead>
                  <TableHead>Work</TableHead>
                  <TableHead>Committed</TableHead>
                  <TableHead>Forecast</TableHead>
                  <TableHead>Health</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {items.map((item) => (
                  <TableRow
                    key={item.id}
                    className="cursor-pointer"
                    onClick={() => router.push(`/commitments/${item.id}`)}
                  >
                    <TableCell className="font-medium">{item.customer_name}</TableCell>
                    <TableCell className="max-w-sm whitespace-normal text-muted-foreground">
                      {item.title}
                    </TableCell>
                    <TableCell className="font-mono text-xs">
                      {formatDate(item.committed_deadline)}
                    </TableCell>
                    <TableCell className="font-mono text-xs">
                      {formatDate(item.current_forecast)}
                    </TableCell>
                    <TableCell>
                      <Badge variant={item.health === "AT_RISK" ? "destructive" : "secondary"}>
                        {healthLabel(item.health)}
                      </Badge>
                    </TableCell>
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
