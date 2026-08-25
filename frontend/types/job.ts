export interface ExperienceRequirements {
  years_min: number | null;
  years_max: number | null;
  seniority_level: string | null;
  description: string | null;
}

export interface JobAnalysisResult {
  id: string;
  cached: boolean;
  job_title: string | null;
  company: string | null;
  required_skills: string[];
  preferred_skills: string[];
  experience_requirements: ExperienceRequirements | null;
  education_requirements: string[];
  tools: string[];
  technologies: string[];
  responsibilities: string[];
  keywords: string[];
  target_resume_id: string | null;
  target_resume_version_id: string | null;
  analyzed_at: string | null;
  prompt_version: string;
  has_embedding: boolean;
}

export interface JobListItem {
  id: string;
  title: string;
  company: string | null;
  job_title: string | null;
  created_at: string;
  updated_at: string;
  has_embedding: boolean;
  required_skills_count: number;
}

export type JobAnalyzeStage =
  | "idle"
  | "reading"
  | "extracting"
  | "done"
  | "error";

export const JOB_ANALYZE_STAGES = [
  { key: "reading" as const, label: "Reading job description" },
  { key: "extracting" as const, label: "Extracting requirements" },
  { key: "done" as const, label: "Done" },
];

export interface AnalyzeJobRequest {
  raw_text: string;
  company?: string | null;
  resume_id?: string | null;
  resume_version_id?: string | null;
}
