"use client";

import Link from "next/link";

import { AppShell } from "@/components/app-shell";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useGaps, useProgress, useResumes, useSessions } from "@/lib/api/hooks";

export default function DashboardPage() {
  const resumes = useResumes();
  const sessions = useSessions();
  const gaps = useGaps();
  const progress = useProgress();

  return (
    <AppShell>
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Candidate dashboard</h1>
          <p className="text-sm text-muted-foreground">
            Resume status, recent interviews, and recurring gaps. Scores are coaching signals, not hire probabilities.
          </p>
        </div>
        <div className="grid gap-4 md:grid-cols-3">
          <StatCard
            title="Resumes"
            loading={resumes.isLoading}
            value={resumes.data?.length ?? 0}
            empty={!resumes.data?.length}
          />
          <StatCard
            title="Completed interviews"
            loading={progress.isLoading}
            value={(progress.data?.completed_sessions as number) ?? 0}
          />
          <StatCard
            title="Open skill gaps"
            loading={gaps.isLoading}
            value={gaps.data?.filter((gap) => gap.status !== "reassessed").length ?? 0}
          />
        </div>
        <div className="grid gap-4 lg:grid-cols-2">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Recent mock interviews</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {sessions.isLoading ? <Skeleton className="h-16" /> : null}
              {sessions.data?.length ? (
                sessions.data.slice(0, 5).map((session) => (
                  <div key={session.id} className="flex items-center justify-between rounded-md border border-border p-3">
                    <div>
                      <p className="text-sm font-medium">{session.mode.replaceAll("_", " ")}</p>
                      <p className="text-xs text-muted-foreground">
                        {session.difficulty} · {session.status}
                      </p>
                    </div>
                    <Button asChild size="sm" variant="outline">
                      <Link href={session.status === "complete" ? `/reports/${session.id}` : `/interview/${session.id}`}>
                        Open
                      </Link>
                    </Button>
                  </div>
                ))
              ) : (
                <Empty text="No interviews yet." href="/interview" action="Set up an interview" />
              )}
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Recurring gaps</CardTitle>
            </CardHeader>
            <CardContent className="flex flex-wrap gap-2">
              {gaps.data?.length ? (
                gaps.data.slice(0, 8).map((gap) => (
                  <Badge key={gap.id} variant={gap.status === "reassessed" ? "secondary" : "outline"}>
                    {gap.skill} · {gap.status} · x{gap.recurrence}
                  </Badge>
                ))
              ) : (
                <p className="text-sm text-muted-foreground">Gaps appear after a completed interview.</p>
              )}
            </CardContent>
          </Card>
        </div>
        <Alert>
          <AlertTitle>Evidence categories stay separate</AlertTitle>
          <AlertDescription>
            Resume facts, job-description inferences, your answers, deterministic measurements, and LLM
            interpretations are labeled in reports so they are never mixed.
          </AlertDescription>
        </Alert>
      </div>
    </AppShell>
  );
}

function StatCard({
  title,
  value,
  loading,
  empty,
}: {
  title: string;
  value: number;
  loading?: boolean;
  empty?: boolean;
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm text-muted-foreground">{title}</CardTitle>
      </CardHeader>
      <CardContent>
        {loading ? <Skeleton className="h-8 w-16" /> : <p className="text-3xl font-semibold">{value}</p>}
        {empty ? <p className="mt-2 text-xs text-muted-foreground">Upload a resume to begin.</p> : null}
      </CardContent>
    </Card>
  );
}

function Empty({ text, href, action }: { text: string; href: string; action: string }) {
  return (
    <div className="space-y-3 text-sm text-muted-foreground">
      <p>{text}</p>
      <Button asChild size="sm">
        <Link href={href}>{action}</Link>
      </Button>
    </div>
  );
}
