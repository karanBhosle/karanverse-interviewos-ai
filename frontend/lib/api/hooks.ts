"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api/client";
import type {
  JobDetail,
  JobMatch,
  LearningPlan,
  ResumeDetail,
  ResumeSummary,
  Session,
  SkillGap,
  UserProfile,
} from "@/types";

export function useMe() {
  return useQuery({
    queryKey: ["me"],
    queryFn: () => api.get<UserProfile>("/api/v1/auth/me"),
    retry: false,
  });
}

export function useResumes() {
  return useQuery({ queryKey: ["resumes"], queryFn: () => api.get<ResumeSummary[]>("/api/v1/resumes") });
}

export function useResume(id?: string) {
  return useQuery({
    queryKey: ["resumes", id],
    enabled: Boolean(id),
    queryFn: () => api.get<ResumeDetail>(`/api/v1/resumes/${id}`),
  });
}

export function useJobs() {
  return useQuery({ queryKey: ["jobs"], queryFn: () => api.get<JobDetail[]>("/api/v1/jobs") });
}

export function useSessions() {
  return useQuery({ queryKey: ["sessions"], queryFn: () => api.get<Session[]>("/api/v1/interview-sessions") });
}

export function useSession(id?: string) {
  return useQuery({
    queryKey: ["sessions", id],
    enabled: Boolean(id),
    queryFn: () => api.get<Session>(`/api/v1/interview-sessions/${id}`),
  });
}

export function useReport(id?: string) {
  return useQuery({
    queryKey: ["report", id],
    enabled: Boolean(id),
    queryFn: () => api.get<Record<string, unknown>>(`/api/v1/interview-sessions/${id}/report`),
  });
}

export function useGaps() {
  return useQuery({ queryKey: ["gaps"], queryFn: () => api.get<SkillGap[]>("/api/v1/skill-gaps") });
}

export function usePlans() {
  return useQuery({ queryKey: ["plans"], queryFn: () => api.get<LearningPlan[]>("/api/v1/learning-plans") });
}

export function useProgress() {
  return useQuery({
    queryKey: ["progress"],
    queryFn: () => api.get<Record<string, unknown>>("/api/v1/analytics/progress"),
  });
}

export function useUploadResume() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (file: File) => {
      const body = new FormData();
      body.append("file", file);
      return api.post<ResumeSummary>("/api/v1/resumes", body);
    },
    onSuccess: () => client.invalidateQueries({ queryKey: ["resumes"] }),
  });
}

export function useCreateJob() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (payload: { title: string; company?: string; raw_text: string }) =>
      api.post<JobDetail>("/api/v1/jobs", payload),
    onSuccess: () => client.invalidateQueries({ queryKey: ["jobs"] }),
  });
}

export function useCreateMatch() {
  return useMutation({
    mutationFn: (payload: { resume_id: string; job_id: string }) =>
      api.post<JobMatch>("/api/v1/job-matches", payload),
  });
}
