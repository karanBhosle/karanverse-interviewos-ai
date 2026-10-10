"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { AppShell } from "@/components/app-shell";
import { useWebcam } from "@/features/video-feedback/use-webcam";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Textarea } from "@/components/ui/textarea";
import { api } from "@/lib/api/client";
import { useSession } from "@/lib/api/hooks";
import type { Evaluation, Session } from "@/types";

export function InterviewRoom({ sessionId }: { sessionId: string }) {
  const router = useRouter();
  const query = useSession(sessionId);
  const [session, setSession] = useState<Session | null>(null);
  const [answer, setAnswer] = useState("");
  const [evaluation, setEvaluation] = useState<Evaluation | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [elapsed, setElapsed] = useState(0);
  const current = session ?? query.data;
  const webcam = useWebcam(Boolean(current?.webcam_assisted && current.visual_consent));

  useEffect(() => {
    if (query.data) setSession(query.data);
  }, [query.data]);

  useEffect(() => {
    setElapsed(0);
    const timer = window.setInterval(() => setElapsed((value) => value + 1), 1000);
    return () => window.clearInterval(timer);
  }, [session?.current_question?.id]);
  const question = current?.current_question;

  if (query.isLoading && !current) {
    return (
      <AppShell>
        <p className="text-sm text-muted-foreground">Loading session…</p>
      </AppShell>
    );
  }
  if (query.isError) {
    return (
      <AppShell>
        <Alert variant="destructive">
          <AlertTitle>Could not load the session</AlertTitle>
          <AlertDescription>Return to history and open the session again.</AlertDescription>
        </Alert>
      </AppShell>
    );
  }

  return (
    <AppShell>
      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_280px]">
        <div className="space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h1 className="text-2xl font-semibold">Interview room</h1>
              <p className="text-sm text-muted-foreground">
                {current?.mode.replaceAll("_", " ")} · {current?.difficulty}
              </p>
            </div>
            <Badge variant={current?.provider_available ? "default" : "secondary"}>
              {current?.provider_available ? "LLM provider available" : "Deterministic evaluation only"}
            </Badge>
          </div>
          <Progress value={Math.min(100, ((current?.covered_competencies.length ?? 0) / 6) * 100)} />
          {question ? (
            <Card>
              <CardHeader>
                <CardTitle className="text-base">
                  {question.is_follow_up ? "Follow-up" : "Question"} · {question.topic}
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <p>{question.prompt}</p>
                <p className="text-xs text-muted-foreground">Learning objective: {question.learning_objective}</p>
                <Textarea
                  rows={10}
                  value={answer}
                  onChange={(event) => setAnswer(event.target.value)}
                  placeholder="Write a structured answer. Reference answers stay hidden unless you request help."
                />
                <div className="flex flex-wrap gap-2">
                  <Button
                    onClick={async () => {
                      if (!current || !question) return;
                      try {
                        const result = await api.post<{ session: Session; evaluation: Evaluation }>(
                          `/api/v1/interview-sessions/${current.id}/answers`,
                          {
                            question_id: question.id,
                            raw_text: answer,
                            duration_seconds: elapsed,
                            visual_features:
                              current.visual_consent && webcam.active ? webcam.sampleLocalFeatures() : undefined,
                          },
                        );
                        setSession(result.session);
                        setEvaluation(result.evaluation);
                        setAnswer("");
                        setError(null);
                      } catch (err) {
                        setError(err instanceof Error ? err.message : "Answer could not be saved");
                      }
                    }}
                  >
                    Submit answer
                  </Button>
                  <Button
                    variant="outline"
                    onClick={async () => {
                      if (!current) return;
                      await api.post(`/api/v1/interview-sessions/${current.id}/pause`);
                    }}
                  >
                    Pause
                  </Button>
                  <Button
                    variant="outline"
                    onClick={async () => {
                      if (!current) return;
                      const report = await api.post(`/api/v1/interview-sessions/${current.id}/complete`);
                      if (report) router.push(`/reports/${current.id}`);
                    }}
                  >
                    Complete session
                  </Button>
                </div>
              </CardContent>
            </Card>
          ) : (
            <Alert>
              <AlertTitle>No open question</AlertTitle>
              <AlertDescription>
                Complete the session to generate a saved report, or start another question from history.
              </AlertDescription>
            </Alert>
          )}
          {evaluation ? (
            <Card>
              <CardHeader>
                <CardTitle className="text-base">
                  Score {evaluation.weighted_score} · {evaluation.provenance}
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3 text-sm">
                <p>{evaluation.feedback}</p>
                <div className="grid gap-2 md:grid-cols-2">
                  {evaluation.dimension_scores.map((dimension) => (
                    <div key={dimension.id} className="rounded-md border border-border p-3">
                      <p className="font-medium">
                        {dimension.label}: {dimension.score}/5
                      </p>
                      <p className="text-muted-foreground">{dimension.justification}</p>
                      {dimension.answer_excerpt ? (
                        <p className="mt-1 text-xs">Excerpt: “{dimension.answer_excerpt}”</p>
                      ) : null}
                    </div>
                  ))}
                </div>
                {evaluation.missing_concepts.length ? (
                  <p>Missing concepts: {evaluation.missing_concepts.join(", ")}</p>
                ) : null}
                <p className="text-muted-foreground">{evaluation.limitations.join(" ")}</p>
              </CardContent>
            </Card>
          ) : null}
          {error ? (
            <Alert variant="destructive">
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          ) : null}
        </div>
        <aside className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Session</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2 text-sm text-muted-foreground">
              <p>Elapsed question time: {elapsed}s</p>
              <p>Covered: {current?.covered_competencies.join(", ") || "none yet"}</p>
              <p>Follow-ups used: {current?.follow_up_count}</p>
            </CardContent>
          </Card>
          {current?.webcam_assisted ? (
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Camera</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <video ref={webcam.videoRef} autoPlay muted playsInline className="w-full rounded-md bg-black" />
                <p className="text-xs text-muted-foreground">
                  Status: {webcam.permission}. Live frames stay in the browser unless you later enable server-side
                  analysis in privacy settings.
                </p>
                <div className="flex gap-2">
                  <Button size="sm" onClick={webcam.start} disabled={webcam.active}>
                    Start camera
                  </Button>
                  <Button size="sm" variant="outline" onClick={webcam.stop}>
                    Stop camera
                  </Button>
                </div>
                {webcam.error ? (
                  <Alert>
                    <AlertDescription>{webcam.error}</AlertDescription>
                  </Alert>
                ) : null}
              </CardContent>
            </Card>
          ) : (
            <Alert>
              <AlertTitle>Text-only mode</AlertTitle>
              <AlertDescription>Webcam analysis is disabled for this session.</AlertDescription>
            </Alert>
          )}
        </aside>
      </div>
    </AppShell>
  );
}
