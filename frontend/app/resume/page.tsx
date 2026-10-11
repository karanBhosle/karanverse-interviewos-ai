"use client";

import { useRef, useState } from "react";

import { AppShell } from "@/components/app-shell";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { api } from "@/lib/api/client";
import { useCreateJob, useCreateMatch, useJobs, useResume, useResumes, useUploadResume } from "@/lib/api/hooks";
import type { JobDetail, JobMatch } from "@/types";

const MIN_JOB_CHARS = 8;

export default function ResumePage() {
  const resumes = useResumes();
  const [selected, setSelected] = useState<string>();
  const resume = useResume(selected ?? resumes.data?.[0]?.id);
  const jobs = useJobs();
  const upload = useUploadResume();
  const createJob = useCreateJob();
  const match = useCreateMatch();
  const fileInput = useRef<HTMLInputElement>(null);
  const [resumeText, setResumeText] = useState("");
  const [jobTitle, setJobTitle] = useState("ML Engineer");
  const [jobText, setJobText] = useState("");
  const [selectedJob, setSelectedJob] = useState<string>();
  const [savedJob, setSavedJob] = useState<JobDetail | null>(null);
  const [matchResult, setMatchResult] = useState<JobMatch | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const selectedJobId = selectedJob ?? savedJob?.id;
  const selectedJobDetail = savedJob?.id === selectedJobId ? savedJob : jobs.data?.find((job) => job.id === selectedJobId);

  function fail(err: unknown) {
    setNotice(null);
    setError(err instanceof Error ? err.message : "Request failed");
  }

  function uploadFile(file: File) {
    setError(null);
    setNotice(`Uploading ${file.name}…`);
    upload.mutate(file, {
      onSuccess: (data) => {
        setSelected(data.id);
        setNotice(`Saved ${data.original_filename}. Review the extracted skills below.`);
        if (fileInput.current) fileInput.current.value = "";
      },
      onError: fail,
    });
  }

  return (
    <AppShell>
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-semibold">Resume workspace</h1>
          <p className="text-sm text-muted-foreground">
            Alignment uses similarity search over your resume and the job description. Comparing also prepares
            the live interview questions from this resume and JD. Those questions are not shown here.
          </p>
        </div>
        <div className="grid gap-4 lg:grid-cols-2">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Upload PDF, DOCX, or paste text</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <Label htmlFor="resume-file">Resume file</Label>
              <Input
                id="resume-file"
                ref={fileInput}
                type="file"
                accept=".pdf,.docx,.txt,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,text/plain"
                disabled={upload.isPending}
                onChange={(event) => {
                  const file = event.target.files?.[0];
                  if (file) uploadFile(file);
                }}
              />
              <Label htmlFor="resume-text">Or paste resume text</Label>
              <Textarea
                id="resume-text"
                rows={8}
                value={resumeText}
                placeholder="Name, skills, experience, and projects…"
                onChange={(event) => setResumeText(event.target.value)}
              />
              <Button
                type="button"
                variant="outline"
                disabled={upload.isPending || resumeText.trim().length < 20}
                onClick={() =>
                  uploadFile(new File([resumeText], "pasted-resume.txt", { type: "text/plain" }))
                }
              >
                {upload.isPending ? "Saving resume…" : "Save pasted resume"}
              </Button>
              <div className="flex flex-wrap gap-2">
                {resumes.data?.map((item) => (
                  <Button
                    key={item.id}
                    size="sm"
                    variant={item.id === (selected ?? resume.data?.id) ? "default" : "outline"}
                    onClick={() => setSelected(item.id)}
                  >
                    {item.original_filename}
                  </Button>
                ))}
              </div>
              {resume.data?.warnings?.map((warning) => (
                <Alert key={warning}>
                  <AlertDescription>{warning}</AlertDescription>
                </Alert>
              ))}
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Target job description</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <Label htmlFor="job-title">Title</Label>
              <Input id="job-title" value={jobTitle} onChange={(event) => setJobTitle(event.target.value)} />
              <Label htmlFor="job-text">Paste the job description</Label>
              <Textarea
                id="job-text"
                rows={8}
                value={jobText}
                placeholder="Paste the full job description, including required skills."
                onChange={(event) => setJobText(event.target.value)}
              />
              <p className="text-xs text-muted-foreground">{jobText.trim().length} characters</p>
              <Button
                type="button"
                disabled={createJob.isPending || jobTitle.trim().length < 2 || jobText.trim().length < MIN_JOB_CHARS}
                onClick={() => {
                  setError(null);
                  setNotice("Extracting requirements…");
                  createJob.mutate(
                    { title: jobTitle.trim(), raw_text: jobText.trim() },
                    {
                      onSuccess: (job) => {
                        setSelectedJob(job.id);
                        setSavedJob(job);
                        setNotice(
                          job.requirements.length
                            ? `Saved “${job.title}” with ${job.requirements.length} extracted requirements.`
                            : `Saved “${job.title}”. No structured requirements were detected — add bullet skills or known terms such as Python or RAG.`,
                        );
                      },
                      onError: fail,
                    },
                  );
                }}
              >
                {createJob.isPending ? "Extracting…" : "Extract requirements"}
              </Button>
              <div className="flex flex-wrap gap-2">
                {jobs.data?.map((job) => (
                  <Button
                    key={job.id}
                    size="sm"
                    variant={job.id === selectedJobId ? "default" : "outline"}
                    onClick={() => {
                      setSelectedJob(job.id);
                      setSavedJob(job);
                    }}
                  >
                    {job.title}
                  </Button>
                ))}
              </div>
              {selectedJobDetail?.requirements?.length ? (
                <div className="space-y-2 rounded-md border border-border p-3">
                  <p className="text-sm font-medium">Extracted requirements</p>
                  {selectedJobDetail.requirements.map((requirement) => (
                    <div key={requirement.id} className="text-sm">
                      <span className="font-medium">{requirement.skill}</span>
                      <span className="text-muted-foreground"> — {requirement.description}</span>
                    </div>
                  ))}
                </div>
              ) : null}
            </CardContent>
          </Card>
        </div>
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Extracted skills</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {resume.data?.structured?.skills?.length ? (
              resume.data.structured.skills.map((skill) => (
                <div key={`${skill.skill_normalized}-${skill.source_page}`} className="rounded-md border border-border p-3">
                  <div className="flex flex-wrap items-center gap-2">
                    <p className="font-medium">{skill.skill_normalized}</p>
                    <Badge variant={skill.evidence_kind === "demonstrated" ? "default" : "secondary"}>
                      {skill.evidence_kind === "demonstrated" ? "demonstrated evidence" : "keyword presence"}
                    </Badge>
                    <span className="text-xs text-muted-foreground">
                      {skill.source_section} {skill.source_page ? `p.${skill.source_page}` : ""}
                    </span>
                  </div>
                  <p className="mt-2 text-sm text-muted-foreground">{skill.evidence_text}</p>
                </div>
              ))
            ) : (
              <p className="text-sm text-muted-foreground">Upload or paste a resume to review extracted facts.</p>
            )}
          </CardContent>
        </Card>
        <div className="flex flex-wrap gap-3">
          <Button
            disabled={!resume.data || !selectedJobId || match.isPending}
            onClick={() =>
              match.mutate(
                { resume_id: resume.data!.id, job_id: selectedJobId! },
                { onSuccess: setMatchResult, onError: fail },
              )
            }
          >
            {match.isPending ? "Comparing…" : "Compare resume to job"}
          </Button>
          {resume.data ? (
            <Button
              variant="outline"
              onClick={() =>
                api.delete(`/api/v1/resumes/${resume.data!.id}`).then(() => {
                  setSelected(undefined);
                  setMatchResult(null);
                  window.location.reload();
                })
              }
            >
              Delete this resume
            </Button>
          ) : null}
        </div>
        {notice ? (
          <Alert>
            <AlertDescription>{notice}</AlertDescription>
          </Alert>
        ) : null}
        {error ? (
          <Alert variant="destructive">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        ) : null}
        {matchResult ? (
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Alignment score {matchResult.alignment_score}</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 text-sm">
              <p className="text-muted-foreground">{matchResult.score_explanation}</p>
              <p>
                Strong {matchResult.strong_count} · Partial {matchResult.partial_count} · Missing {matchResult.missing_count}
              </p>
              {matchResult.items.map((item) => (
                <div key={item.skill} className="rounded-md border border-border p-3">
                  <div className="flex flex-wrap items-center gap-2">
                    <strong>{item.skill}</strong>
                    <Badge variant="outline">{item.matching_status}</Badge>
                    <Badge variant="secondary">{item.evidence_strength}</Badge>
                  </div>
                  <p className="mt-1 text-muted-foreground">{item.description}</p>
                  {item.evidence_found ? (
                    <p className="mt-1">
                      Evidence: {item.evidence_found} ({item.evidence_source})
                    </p>
                  ) : (
                    <p className="mt-1">No resume evidence found.</p>
                  )}
                  {item.match_method ? (
                    <p className="mt-1 text-xs text-muted-foreground">
                      Similarity {item.similarity_score ?? 0}
                    </p>
                  ) : null}
                </div>
              ))}
              {matchResult.questions_prepared ? (
                <p className="pt-2 text-sm text-muted-foreground">
                  Live interview questions are prepared from this comparison and will only be asked in the session.
                </p>
              ) : null}
            </CardContent>
          </Card>
        ) : null}
      </div>
    </AppShell>
  );
}
