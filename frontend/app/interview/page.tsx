"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { AppShell } from "@/components/app-shell";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api } from "@/lib/api/client";
import { useJobs, useResumes } from "@/lib/api/hooks";
import type { Session } from "@/types";

const MODES = [
  ["mixed", "Mixed interview"],
  ["technical_fundamentals", "Technical fundamentals"],
  ["python_coding", "Python and coding"],
  ["machine_learning", "Machine learning"],
  ["genai_llms", "GenAI and LLMs"],
  ["rag_hybrid_retrieval", "RAG and hybrid retrieval"],
  ["agentic_ai_langgraph", "Agentic AI and LangGraph"],
  ["system_design", "System design"],
  ["project_deep_dive", "Project deep dive"],
  ["behavioral", "Behavioral"],
];

export default function InterviewSetupPage() {
  const resumes = useResumes();
  const jobs = useJobs();
  const router = useRouter();
  const [mode, setMode] = useState("mixed");
  const [difficulty, setDifficulty] = useState("medium");
  const [duration, setDuration] = useState(30);
  const [role, setRole] = useState("Data Scientist");
  const [resumeId, setResumeId] = useState<string>();
  const [jobId, setJobId] = useState<string>();
  const [webcam, setWebcam] = useState(false);
  const [speech, setSpeech] = useState(true);
  const [faceToFace, setFaceToFace] = useState(false);
  const [consent, setConsent] = useState(false);
  const [speechConsent, setSpeechConsent] = useState(false);
  const [error, setError] = useState<string | null>(null);

  return (
    <AppShell>
      <div className="mx-auto max-w-3xl space-y-6">
        <div>
          <h1 className="text-2xl font-semibold">Interview setup</h1>
          <p className="text-sm text-muted-foreground">
            Choose a mode, duration, and whether this session is spoken face-to-face or text-only.
          </p>
        </div>
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Session configuration</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label>Target role</Label>
              <Input value={role} onChange={(event) => setRole(event.target.value)} />
            </div>
            <div className="grid gap-4 md:grid-cols-2">
              <label className="space-y-2 text-sm">
                Interview type
                <select
                  className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 text-sm"
                  value={mode}
                  onChange={(event) => setMode(event.target.value)}
                >
                  {MODES.map(([value, label]) => (
                    <option key={value} value={value}>
                      {label}
                    </option>
                  ))}
                </select>
              </label>
              <label className="space-y-2 text-sm">
                Difficulty
                <select
                  className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 text-sm"
                  value={difficulty}
                  onChange={(event) => setDifficulty(event.target.value)}
                >
                  <option value="easy">Easy</option>
                  <option value="medium">Medium</option>
                  <option value="hard">Hard</option>
                </select>
              </label>
            </div>
            <label className="space-y-2 text-sm">
              Duration (minutes)
              <Input
                type="number"
                min={10}
                max={90}
                value={duration}
                onChange={(event) => setDuration(Number(event.target.value))}
              />
            </label>
            <label className="space-y-2 text-sm">
              Resume
              <select
                className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 text-sm"
                value={resumeId ?? ""}
                onChange={(event) => setResumeId(event.target.value || undefined)}
              >
                <option value="">None</option>
                {resumes.data?.map((resume) => (
                  <option key={resume.id} value={resume.id}>
                    {resume.original_filename}
                  </option>
                ))}
              </select>
            </label>
            <label className="space-y-2 text-sm">
              Job description
              <select
                className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 text-sm"
                value={jobId ?? ""}
                onChange={(event) => setJobId(event.target.value || undefined)}
              >
                <option value="">None</option>
                {jobs.data?.map((job) => (
                  <option key={job.id} value={job.id}>
                    {job.title}
                  </option>
                ))}
              </select>
            </label>
            <label className="flex items-start gap-3 text-sm">
              <Checkbox
                checked={faceToFace}
                onCheckedChange={(value) => {
                  const next = Boolean(value);
                  setFaceToFace(next);
                  if (next) {
                    setWebcam(true);
                    setSpeech(true);
                  }
                }}
              />
              <span>
                Face-to-face spoken interview. The interviewer reads each question aloud, you answer out loud, and
                the camera stays on for presence. Audio is transcribed in the browser and is not uploaded.
              </span>
            </label>
            <label className="flex items-start gap-3 text-sm">
              <Checkbox checked={speech} onCheckedChange={(value) => setSpeech(Boolean(value))} />
              <span>
                Spoken answers. Record your voice, convert it to text, then score the transcript. You can still
                edit the transcript before submit.
              </span>
            </label>
            <label className="flex items-start gap-3 text-sm">
              <Checkbox checked={webcam} onCheckedChange={(value) => setWebcam(Boolean(value))} />
              <span>
                Enable optional webcam-assisted mode. Frames are processed locally by default. Denying camera
                permission still allows a full spoken or typed interview.
              </span>
            </label>
            {speech ? (
              <label className="flex items-start gap-3 text-sm">
                <Checkbox checked={speechConsent} onCheckedChange={(value) => setSpeechConsent(Boolean(value))} />
                <span>
                  I consent to microphone use. My spoken answers will be transcribed in the browser. Audio is not
                  uploaded unless I later change privacy settings.
                </span>
              </label>
            ) : null}
            {webcam ? (
              <label className="flex items-start gap-3 text-sm">
                <Checkbox checked={consent} onCheckedChange={(value) => setConsent(Boolean(value))} />
                <span>
                  I consent to local visual analysis of face visibility, head-orientation variation, and recording
                  quality. I understand this will not infer emotion, honesty, or nervousness.
                </span>
              </label>
            ) : null}
            {error ? (
              <Alert variant="destructive">
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            ) : null}
            <Button
              disabled={(speech && !speechConsent) || (webcam && !consent)}
              onClick={async () => {
                if (speech && !speechConsent) {
                  setError("Consent to microphone use before starting a spoken interview.");
                  return;
                }
                if (webcam && !consent) {
                  setError("Consent to camera use before starting a webcam-assisted interview.");
                  return;
                }
                try {
                  const plan = await api.post<{ id: string }>("/api/v1/interview-plans", {
                    resume_id: resumeId,
                    job_id: jobId,
                    target_role: role,
                    mode,
                    difficulty,
                    duration_minutes: duration,
                    webcam_assisted: webcam,
                  });
                  const session = await api.post<Session>("/api/v1/interview-sessions", {
                    plan_id: plan.id,
                    visual_consent: webcam && consent,
                    speech_assisted: speech,
                  });
                  router.push(`/interview/${session.id}`);
                } catch (err) {
                  setError(err instanceof Error ? err.message : "Could not start the session");
                }
              }}
            >
              Start interview
            </Button>
          </CardContent>
        </Card>
      </div>
    </AppShell>
  );
}
