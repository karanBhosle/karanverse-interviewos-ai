"use client";

import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip } from "recharts";

import { AppShell } from "@/components/app-shell";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useReport } from "@/lib/api/hooks";

export function ReportView({ sessionId }: { sessionId: string }) {
  const report = useReport(sessionId);
  const data = report.data;

  return (
    <AppShell>
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-semibold">Evaluation report</h1>
          <p className="text-sm text-muted-foreground">
            Technical scores, evidence excerpts, and optional visual observations stay on separate scales.
          </p>
        </div>
        {report.isLoading ? <Skeleton className="h-40" /> : null}
        {report.isError ? (
          <Alert variant="destructive">
            <AlertTitle>Report unavailable</AlertTitle>
            <AlertDescription>Complete the session first. Partial reports are not invented.</AlertDescription>
          </Alert>
        ) : null}
        {data ? (
          <>
            <div className="grid gap-4 md:grid-cols-3">
              <Card>
                <CardHeader>
                  <CardTitle className="text-sm text-muted-foreground">Technical answer score</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-3xl font-semibold">{String(data.technical_answer_score ?? "n/a")}</p>
                  <p className="mt-2 text-xs text-muted-foreground">{String(data.score_provenance ?? "")}</p>
                </CardContent>
              </Card>
              <Card>
                <CardHeader>
                  <CardTitle className="text-sm text-muted-foreground">Coverage</CardTitle>
                </CardHeader>
                <CardContent className="text-sm">
                  {((data.topic_coverage as { covered?: string[] })?.covered ?? []).join(", ") || "None recorded"}
                </CardContent>
              </Card>
              <Card>
                <CardHeader>
                  <CardTitle className="text-sm text-muted-foreground">Provider</CardTitle>
                </CardHeader>
                <CardContent>
                  <Badge variant={data.provider_available ? "default" : "secondary"}>
                    {data.provider_available ? "LLM evaluation used" : "Deterministic only"}
                  </Badge>
                </CardContent>
              </Card>
            </div>
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Competency scores</CardTitle>
              </CardHeader>
              <CardContent className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart
                    data={Object.entries(
                      ((data.topic_coverage as { competency_scores?: Record<string, number> })?.competency_scores ??
                        {}) as Record<string, number>,
                    ).map(([name, score]) => ({ name, score }))}
                  >
                    <XAxis dataKey="name" />
                    <YAxis domain={[0, 100]} />
                    <Tooltip />
                    <Bar dataKey="score" fill="var(--color-chart-2)" />
                  </BarChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
            {((data.answers as Array<Record<string, unknown>>) ?? []).map((item, index) => (
              <Card key={index}>
                <CardHeader>
                  <CardTitle className="text-base">{String(item.topic)}</CardTitle>
                </CardHeader>
                <CardContent className="space-y-2 text-sm">
                  <p>{String(item.question)}</p>
                  <p className="text-muted-foreground">Your answer: {String(item.answer ?? "—")}</p>
                  {item.evaluation ? (
                    <>
                      <p>Score {(item.evaluation as { weighted_score: number }).weighted_score}</p>
                      <p>{(item.evaluation as { feedback: string }).feedback}</p>
                      <p>
                        Missing:{" "}
                        {((item.evaluation as { missing_concepts: string[] }).missing_concepts ?? []).join(", ") ||
                          "none"}
                      </p>
                      <p className="text-muted-foreground">
                        Stronger answer: {(item.evaluation as { suggested_stronger_answer: string }).suggested_stronger_answer}
                      </p>
                    </>
                  ) : (
                    <p>No evaluation stored for this question.</p>
                  )}
                </CardContent>
              </Card>
            ))}
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Optional visual observations</CardTitle>
              </CardHeader>
              <CardContent className="text-sm text-muted-foreground">
                {((data.visual_observations as unknown[]) ?? []).length ? (
                  <pre className="whitespace-pre-wrap font-mono text-xs">
                    {JSON.stringify(data.visual_observations, null, 2)}
                  </pre>
                ) : (
                  <p>No visual data. Camera denial or text-only mode is not penalized.</p>
                )}
              </CardContent>
            </Card>
            <Alert>
              <AlertTitle>Limitations</AlertTitle>
              <AlertDescription>{((data.limitations as string[]) ?? []).join(" ")}</AlertDescription>
            </Alert>
          </>
        ) : null}
      </div>
    </AppShell>
  );
}
