"use client";

import Link from "next/link";
import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { AppShell } from "@/components/app-shell";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useProgress, useSessions } from "@/lib/api/hooks";

export default function HistoryPage() {
  const sessions = useSessions();
  const progress = useProgress();
  const points = ((progress.data?.sessions as Array<Record<string, unknown>>) ?? []).filter(
    (item) => item.mean_score != null,
  );

  return (
    <AppShell>
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-semibold">Session history</h1>
          <p className="text-sm text-muted-foreground">
            Compare only sessions that share mode, difficulty, and rubric version.
          </p>
        </div>
        <Alert>
          <AlertDescription>
            Raw scores from unlike sessions are not directly comparable. Difficulty and rubric version are shown for
            every point.
          </AlertDescription>
        </Alert>
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Score trend</CardTitle>
          </CardHeader>
          <CardContent className="h-64">
            {points.length ? (
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={points.map((item) => ({ ...item, label: String(item.mode) }))}>
                  <XAxis dataKey="label" />
                  <YAxis domain={[0, 100]} />
                  <Tooltip />
                  <Line type="monotone" dataKey="mean_score" stroke="var(--color-chart-2)" />
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <p className="text-sm text-muted-foreground">Complete a session to see a trend.</p>
            )}
          </CardContent>
        </Card>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Mode</TableHead>
              <TableHead>Difficulty</TableHead>
              <TableHead>Status</TableHead>
              <TableHead />
            </TableRow>
          </TableHeader>
          <TableBody>
            {sessions.data?.map((session) => (
              <TableRow key={session.id}>
                <TableCell>{session.mode.replaceAll("_", " ")}</TableCell>
                <TableCell>{session.difficulty}</TableCell>
                <TableCell>{session.status}</TableCell>
                <TableCell>
                  <Button asChild size="sm" variant="outline">
                    <Link href={session.status === "complete" ? `/reports/${session.id}` : `/interview/${session.id}`}>
                      Open
                    </Link>
                  </Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </AppShell>
  );
}
