export type ResumeSummary = {
  id: string;
  original_filename: string;
  content_type: string;
  size_bytes: number;
  status: string;
};

export type ResumeDetail = ResumeSummary & {
  latest_version_id: string | null;
  structured: {
    skills?: Array<{
      skill_normalized: string;
      evidence_kind: string;
      evidence_text: string;
      source_section: string | null;
      source_page: number | null;
    }>;
    roles?: Array<Record<string, unknown>>;
    projects?: Array<Record<string, unknown>>;
    achievements?: Array<Record<string, unknown>>;
    technologies?: string[];
    warnings?: string[];
  } | null;
  extracted_text: string | null;
  warnings: string[];
};

export type JobDetail = {
  id: string;
  title: string;
  company: string | null;
  seniority: string | null;
  raw_text: string;
  requirements: Array<{
    id: string;
    skill: string;
    description: string;
    importance: string;
    weight: number;
  }>;
};

export type JobMatch = {
  id: string;
  alignment_score: number;
  score_explanation: string;
  strong_count: number;
  partial_count: number;
  missing_count: number;
  items: Array<{
    skill: string;
    description: string;
    importance: string;
    evidence_found: string | null;
    evidence_source: string | null;
    evidence_strength: string;
    matching_status: string;
    follow_up_questions: string[];
  }>;
};

export type Question = {
  id: string;
  question_key: string;
  topic: string;
  difficulty: string;
  prompt: string;
  learning_objective: string;
  sequence: number;
  hints_available: boolean;
  help_revealed: boolean;
  is_follow_up: boolean;
  reference_guidance: string | null;
};

export type Session = {
  id: string;
  status: string;
  mode: string;
  difficulty: string;
  duration_minutes: number;
  webcam_assisted: boolean;
  visual_consent: boolean;
  covered_competencies: string[];
  uncovered_competencies: string[];
  follow_up_count: number;
  provider_available: boolean;
  speech_assisted: boolean;
  current_question: Question | null;
};

export type InterviewerTurn = {
  spoken: string;
  tone: string;
};

export type Evaluation = {
  weighted_score: number;
  provenance: string;
  evaluation_model: string | null;
  rubric_version: string;
  dimension_scores: Array<{
    id: string;
    label: string;
    weight: number;
    score: number;
    justification: string;
    answer_excerpt: string;
  }>;
  evidence_excerpts: string[];
  missing_concepts: string[];
  incorrect_claims: string[];
  feedback: string;
  suggested_stronger_answer: string;
  follow_up_recommendation: string;
  limitations: string[];
};

export type SkillGap = {
  id: string;
  skill: string;
  evidence: string;
  why_it_matters: string;
  severity: string;
  job_relevance: string;
  recurrence: number;
  status: string;
};

export type LearningPlan = {
  id: string;
  status: string;
  summary: string;
  tasks: Array<{
    id: string;
    skill: string;
    why_it_matters: string;
    priority: string;
    recommended_reading: string | null;
    search_suggestion: string | null;
    practice_question: string;
    coding_exercise: string | null;
    expected_outcome: string;
    reassessment_criteria: string;
    status: string;
  }>;
};

export type UserProfile = {
  id: string;
  email: string;
  display_name: string;
  resume_retention_enabled: boolean;
  session_history_enabled: boolean;
  camera_consent: boolean;
  media_storage_consent: boolean;
  visual_checklist_enabled: boolean;
  visual_analysis_opt_in: boolean;
};
