export type SkillGapPriority = "high" | "medium" | "low";

export interface MissingSkillGapItem {
  skill: string;
  priority: SkillGapPriority;
  source: string;
  why_it_matters: string;
}

export interface LearningRoadmapStep {
  skill: string;
  rationale: string;
}

export interface SkillGapResult {
  job_match_id: string;
  job_description_id: string;
  resume_id: string;
  resume_version_id: string | null;
  cached: boolean;
  target_role: string | null;
  company: string | null;
  skill_coverage_percent: number;
  coverage_meta: {
    required_count?: number;
    preferred_count?: number;
    matched_weight?: number;
    total_weight?: number;
    formula?: string;
  };
  matched_skills: string[];
  missing_skills: MissingSkillGapItem[];
  learning_roadmap: LearningRoadmapStep[];
  match_score: number;
  analyzed_at: string | null;
  prompt_version: string;
}

export const PRIORITY_LABELS: Record<SkillGapPriority, string> = {
  high: "High priority",
  medium: "Medium priority",
  low: "Low priority",
};
