export type AnalysisSeverity = "high" | "medium" | "low";

export interface DimensionScore {
  key: string;
  score: number;
  explanation: string;
  disclaimer?: string | null;
}

export interface AnalysisIssue {
  severity: string;
  category: string;
  title: string;
  description: string;
  suggested_fix?: string | null;
  grounded_in_resume?: boolean;
}

export interface ResumeAnalysis {
  analysis_id: string;
  resume_id: string;
  resume_version_id?: string | null;
  cached: boolean;
  stale?: boolean;
  overall_score: number | null;
  category_scores: Record<string, number>;
  summary: string;
  dimensions: DimensionScore[];
  issues: AnalysisIssue[];
  status: string;
  analyzed_at: string | null;
  prompt_version: string;
}

export interface LatestJobMatchSummary {
  match_id: string;
  job_description_id: string;
  job_title: string | null;
  company: string | null;
  match_score: number;
  semantic_score: number | null;
  breakdown: {
    skills_match?: number;
    experience_match?: number;
    keyword_match?: number;
    project_relevance?: number;
    education_match?: number;
  } | null;
  summary?: string;
  matched_at: string | null;
  stale?: boolean;
}

export interface ResumeDetail {
  id: string;
  user_id: string | null;
  title: string;
  original_filename: string | null;
  mime_type: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  sections_found: string[];
  sections_missing: string[];
  active_version_id?: string | null;
  active_version_label?: string | null;
  analysis_stale?: boolean;
  match_stale?: boolean;
  reanalyze_recommended?: boolean;
  latest_analysis: ResumeAnalysis | null;
  latest_job_match: LatestJobMatchSummary | null;
}

export interface ResumeListItem {
  id: string;
  title: string;
  original_filename: string | null;
  created_at: string;
  updated_at: string;
  overall_score: number | null;
  analyzed_at: string | null;
  has_analysis: boolean;
}

export const CATEGORY_CONFIG = [
  {
    key: "ats",
    label: "ATS Compatibility",
    dimensionKey: "ats_compatibility",
  },
  {
    key: "job_match",
    label: "Job Match",
    dimensionKey: null,
  },
  {
    key: "skills",
    label: "Skills",
    dimensionKey: "skills",
  },
  {
    key: "content_quality",
    label: "Content Quality",
    dimensionKey: "content_quality",
  },
  {
    key: "projects",
    label: "Projects",
    dimensionKey: "projects",
  },
  {
    key: "experience",
    label: "Experience",
    dimensionKey: "experience",
  },
] as const;

export const DIMENSION_LABELS: Record<string, string> = {
  ats_compatibility: "ATS Compatibility",
  skills: "Skills",
  experience: "Experience",
  projects: "Projects",
  education: "Education",
  certifications: "Certifications",
  achievements: "Achievements",
  professional_summary: "Professional Summary",
  keywords: "Keywords",
  content_quality: "Content Quality",
  readability: "Readability",
  relevance: "Relevance",
  quantifiable_achievements: "Quantifiable Achievements",
  action_verbs: "Action Verbs",
  formatting_issues: "Formatting",
};

export function normalizeSeverity(severity: string): AnalysisSeverity {
  const value = severity.toLowerCase();
  if (value === "high") return "high";
  if (value === "low") return "low";
  return "medium";
}
