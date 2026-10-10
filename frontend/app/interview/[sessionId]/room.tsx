"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";

import { AppShell } from "@/components/app-shell";
import { useSpeechInterview } from "@/features/speech/use-speech-interview";
import { useWebcam } from "@/features/video-feedback/use-webcam";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Progress } from "@/components/ui/progress";
import { Textarea } from "@/components/ui/textarea";
import { api } from "@/lib/api/client";
import { useMe, useSession } from "@/lib/api/hooks";
import type { Evaluation, Session } from "@/types";

function firstName(value?: string | null) {
  const name = (value || "").trim().split(/\s+/)[0];
  return name || "there";
}

export function InterviewRoom({ sessionId }: { sessionId: string }) {
  const router = useRouter();
  const query = useSession(sessionId);
  const me = useMe();
  const [session, setSession] = useState<Session | null>(null);
  const [answer, setAnswer] = useState("");
  const [evaluation, setEvaluation] = useState<Evaluation | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [elapsed, setElapsed] = useState(0);
  const [phase, setPhase] = useState<"welcome" | "asking" | "listening">("welcome");
  const [consent, setConsent] = useState(false);
  const [starting, setStarting] = useState(false);
  const usedSpeechRef = useRef(false);
  const askedQuestionIdRef = useRef<string | null>(null);
  const answerRef = useRef("");
  const current = session ?? query.data;
  const speechAssisted = Boolean(current?.speech_assisted);
  const webcam = useWebcam(Boolean(current?.webcam_assisted && current.visual_consent));
  const speech = useSpeechInterview();
  const question = current?.current_question;
  const candidate = firstName(me.data?.display_name);
  const greeting = `Hi ${candidate}, hope you are doing well. Thank you for joining today. Shall we start the interview?`;
  answerRef.current = answer;

  useEffect(() => {
    if (query.data) setSession(query.data);
  }, [query.data]);

  useEffect(() => {
    setElapsed(0);
    const timer = window.setInterval(() => setElapsed((value) => value + 1), 1000);
    return () => window.clearInterval(timer);
  }, [session?.current_question?.id]);

  useEffect(() => {
    if (!speechAssisted) return;
    const live = [speech.transcript, speech.interim].filter(Boolean).join(" ").trim();
    if (live) setAnswer(live);
  }, [speech.transcript, speech.interim, speechAssisted]);

  const submitAnswer = useCallback(async () => {
    if (!current || !question) return;
    const text = answerRef.current.trim();
    if (!text) return;
    speech.pauseAnswerTurn();
    speech.stopSpeaking();
    try {
      const result = await api.post<{ session: Session; evaluation: Evaluation }>(
        `/api/v1/interview-sessions/${current.id}/answers`,
        {
          question_id: question.id,
          raw_text: text,
          duration_seconds: elapsed,
          transcript_provenance: usedSpeechRef.current ? "speech_to_text" : "typed",
          visual_features: current.visual_consent && webcam.active ? webcam.sampleLocalFeatures() : undefined,
        },
      );
      setSession(result.session);
      setEvaluation(result.evaluation);
      setAnswer("");
      usedSpeechRef.current = speechAssisted;
      speech.resetAnswerAudio();
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Answer could not be saved");
    }
  }, [current, elapsed, question, speech, speechAssisted, webcam]);

  useEffect(() => {
    speech.setOnSilence(() => {
      void submitAnswer();
    });
    return () => speech.setOnSilence(null);
  }, [speech, submitAnswer]);

  const askCurrentQuestion = useCallback(async () => {
    if (!question) return;
    askedQuestionIdRef.current = question.id;
    setPhase("asking");
    setAnswer("");
    speech.resetAnswerAudio();
    usedSpeechRef.current = true;
    await speech.speak(question.prompt);
    await new Promise((resolve) => window.setTimeout(resolve, 450));
    speech.beginAnswerTurn();
    setPhase("listening");
  }, [question, speech]);

  useEffect(() => {
    if (!speechAssisted || phase === "welcome" || !question?.id) return;
    if (askedQuestionIdRef.current === question.id) return;
    void askCurrentQuestion();
  }, [askCurrentQuestion, phase, question?.id, speechAssisted]);

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

  if (speechAssisted && phase === "welcome") {
    return (
      <AppShell>
        <div className="mx-auto max-w-2xl space-y-6">
          <div>
            <h1 className="text-2xl font-semibold">Face-to-face interview</h1>
            <p className="text-sm text-muted-foreground">
              {current?.mode.replaceAll("_", " ")} · {current?.difficulty}
            </p>
          </div>
          <Card>
            <CardContent className="space-y-5 pt-6">
              <p className="text-lg leading-relaxed">{greeting}</p>
              <p className="text-sm text-muted-foreground">
                I will only start after you agree. Use Chrome, same as Ask ELSAA. After the question, tap Start
                speaking and your words appear as you talk.
              </p>
              <label className="flex items-start gap-3 text-sm">
                <Checkbox checked={consent} onCheckedChange={(value) => setConsent(Boolean(value))} />
                <span>
                  I consent to microphone use for this session. My voice will be transcribed in this browser and will
                  not be uploaded as audio.
                </span>
              </label>
              {error || speech.error ? (
                <Alert variant="destructive">
                  <AlertDescription>{error || speech.error}</AlertDescription>
                </Alert>
              ) : null}
              {!speech.supported.stt ? (
                <Alert>
                  <AlertDescription>
                    Live transcription needs Chrome or Safari. Open this page in Chrome, then allow the microphone.
                  </AlertDescription>
                </Alert>
              ) : null}
              <div className="flex flex-wrap gap-2">
                <Button
                  variant="outline"
                  disabled={starting}
                  onClick={() => {
                    void speech.speak(greeting);
                  }}
                >
                  Hear greeting
                </Button>
                <Button
                  disabled={!consent || starting}
                  onClick={async () => {
                    if (!consent || !question) return;
                    askedQuestionIdRef.current = question.id;
                    setStarting(true);
                    setError(null);
                    usedSpeechRef.current = true;
                    try {
                      await speech.armMicrophone();
                      setPhase("asking");
                      await askCurrentQuestion();
                    } catch (err) {
                      askedQuestionIdRef.current = null;
                      setPhase("welcome");
                      setError(
                        err instanceof Error
                          ? err.message
                          : "Allow the microphone, then click Yes, start the interview.",
                      );
                    } finally {
                      setStarting(false);
                    }
                  }}
                >
                  {starting ? speech.listenStatus || "Starting…" : "Yes, start the interview"}
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      </AppShell>
    );
  }

  return (
    <AppShell>
      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_280px]">
        <div className="space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h1 className="text-2xl font-semibold">
                {current?.webcam_assisted && speechAssisted ? "Face-to-face interview" : "Interview room"}
              </h1>
              <p className="text-sm text-muted-foreground">
                {current?.mode.replaceAll("_", " ")} · {current?.difficulty}
              </p>
            </div>
            <div className="flex flex-wrap gap-2">
              {speechAssisted ? (
                <Badge variant="outline">
                  {phase === "listening" ? "Listening" : speech.micReady ? "Microphone ready" : "Interviewer speaking"}
                </Badge>
              ) : null}
              <Badge variant={current?.provider_available ? "default" : "secondary"}>
                {current?.provider_available ? "LLM provider available" : "Deterministic evaluation only"}
              </Badge>
            </div>
          </div>
          <Progress value={Math.min(100, ((current?.covered_competencies.length ?? 0) / 6) * 100)} />
          {question ? (
            <Card>
              <CardContent className="space-y-5 pt-6">
                <p className="text-xl leading-relaxed">{question.prompt}</p>
                {speechAssisted ? (
                  <div className="space-y-3">
                    <div className="min-h-24 rounded-md border border-border bg-muted/30 p-4 text-base leading-relaxed">
                      {[speech.transcript, speech.interim].filter(Boolean).join(" ").trim() || (
                        <span className="text-muted-foreground">
                          {speech.recording
                            ? "Listening — speak now."
                            : "Tap Start speaking, then talk. Your words appear here."}
                        </span>
                      )}
                    </div>
                    {speech.transcript || speech.interim ? (
                      <p className="text-sm text-emerald-400">
                        Heard: {[speech.transcript, speech.interim].filter(Boolean).join(" ")}
                      </p>
                    ) : null}
                    <div className="h-2 overflow-hidden rounded-full bg-muted">
                      <div
                        className="h-full bg-emerald-500 transition-[width]"
                        style={{ width: `${Math.min(100, Math.round(speech.micLevel * 500))}%` }}
                      />
                    </div>
                    <p className="text-sm text-muted-foreground">{speech.listenStatus}</p>
                    {speech.silenceLeft !== null ? (
                      <p className="rounded-md border border-amber-500/40 bg-amber-500/10 px-3 py-2 text-base font-medium">
                        Pause detected. Continuing in {speech.silenceLeft}s. Keep talking to stay on this answer.
                      </p>
                    ) : null}
                    <div className="flex flex-wrap gap-2">
                      <Button
                        variant={speech.recording ? "outline" : "default"}
                        onClick={() => void speech.startSpeaking()}
                      >
                        {speech.recording ? "Listening…" : "Start speaking"}
                      </Button>
                      <Button variant="outline" onClick={() => void submitAnswer()} disabled={!answer.trim()}>
                        I am done
                      </Button>
                    </div>
                    {speech.error ? (
                      <Alert>
                        <AlertDescription>{speech.error}</AlertDescription>
                      </Alert>
                    ) : null}
                  </div>
                ) : (
                  <>
                    <p className="text-xs text-muted-foreground">Learning objective: {question.learning_objective}</p>
                    <Textarea
                      rows={10}
                      value={answer}
                      onChange={(event) => setAnswer(event.target.value)}
                      placeholder="Write a structured answer. Reference answers stay hidden unless you request help."
                    />
                  </>
                )}
                <div className="flex flex-wrap gap-2">
                  {speechAssisted ? null : (
                    <Button onClick={() => void submitAnswer()} disabled={!answer.trim()}>
                      Submit answer
                    </Button>
                  )}
                  <Button
                    variant="outline"
                    onClick={async () => {
                      if (!current) return;
                      speech.stopRecording();
                      await api.post(`/api/v1/interview-sessions/${current.id}/pause`);
                    }}
                  >
                    Pause
                  </Button>
                  <Button
                    variant="outline"
                    onClick={async () => {
                      if (!current) return;
                      speech.stopRecording();
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
          {evaluation && !speechAssisted ? (
            <Card>
              <CardHeader>
                <CardTitle className="text-base">
                  Score {evaluation.weighted_score} · {evaluation.provenance}
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3 text-sm">
                <p>{evaluation.feedback}</p>
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
                <div className="flex gap-2">
                  <Button size="sm" onClick={webcam.start} disabled={webcam.active}>
                    Start camera
                  </Button>
                  <Button size="sm" variant="outline" onClick={webcam.stop}>
                    Stop camera
                  </Button>
                </div>
              </CardContent>
            </Card>
          ) : null}
        </aside>
      </div>
    </AppShell>
  );
}
