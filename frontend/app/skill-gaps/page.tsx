"use client";

import { AppShell } from "@/components/app-shell";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useGaps } from "@/lib/api/hooks";

export default function SkillGapsPage() {
  const gaps = useGaps();
  return (
    <AppShell>
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-semibold">Skill-gap dashboard</h1>
          <p className="text-sm text-muted-foreground">
            Gaps are prioritized by job relevance, severity, and recurrence. Reassessment happens from the learning plan.
          </p>
        </div>
        {gaps.isLoading ? <Skeleton className="h-24" /> : null}
        {gaps.data?.length ? (
          <div className="grid gap-4">
            {gaps.data.map((gap) => (
              <Card key={gap.id}>
                <CardHeader>
                  <CardTitle className="flex flex-wrap items-center gap-2 text-base">
                    {gap.skill}
                    <Badge variant="outline">{gap.status}</Badge>
                    <Badge variant="secondary">{gap.severity}</Badge>
                    <Badge>relevance {gap.job_relevance}</Badge>
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-2 text-sm text-muted-foreground">
                  <p>{gap.evidence}</p>
                  <p>{gap.why_it_matters}</p>
                  <p>Seen {gap.recurrence} time(s).</p>
                </CardContent>
              </Card>
            ))}
          </div>
        ) : (
          <p className="text-sm text-muted-foreground">Complete an interview to populate gaps.</p>
        )}
      </div>
    </AppShell>
  );
}
