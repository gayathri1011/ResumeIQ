export interface MatchBreakdown {
  skills_match: number;
  experience_match: number;
  keyword_match: number;
  project_relevance: number;
  education_match: number;
}

export interface MatchExplanation {
  category: string;
  summary: string;
}

export interface JobMatchResult {
  match_id: string;
  cached: boolean;
  resume_id: string;
  resume_version_id: string | null;
  job_description_id: string;
  job_title: string | null;
  company: string | null;
  match_score: number;
  semantic_score: number | null;
  keyword_score: number | null;
  breakdown: MatchBreakdown;
  matched_skills: string[];
  missing_skills: string[];
  missing_keywords: string[];
  explanations: MatchExplanation[];
  summary: string;
  matched_at: string | null;
  prompt_version: string;
}

export interface LatestJobMatchSummary {
  match_id: string;
  job_description_id: string;
  job_title: string | null;
  company: string | null;
  match_score: number;
  semantic_score: number | null;
  breakdown: MatchBreakdown | null;
  matched_at: string | null;
}

export interface MatchJobRequest {
  resume_id: string;
  resume_version_id?: string | null;
}

export type JobMatchStage = "idle" | "matching" | "done" | "error";

export const MATCH_BREAKDOWN_LABELS: Record<keyof MatchBreakdown, string> = {
  skills_match: "Skills Match",
  experience_match: "Experience Match",
  keyword_match: "Keyword Match",
  project_relevance: "Project Relevance",
  education_match: "Education Match",
};
