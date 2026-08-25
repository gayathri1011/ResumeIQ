export interface OptimizationChange {
  change_id: string;
  section: string;
  field_path?: string | null;
  before: string;
  after: string;
  why: string;
}

export interface OptimizationProposal {
  optimization_id: string;
  resume_id: string;
  draft_version_id: string | null;
  draft_version_number: number | null;
  target_role: string;
  job_description_id?: string | null;
  job_match_id?: string | null;
  optimization_mode: string;
  status: string;
  review_status: string;
  message: string;
  original_content: Record<string, unknown>;
  optimized_content: Record<string, unknown>;
  changes: OptimizationChange[];
  prompt_version: string;
  model_used?: string | null;
  cached: boolean;
  applied_change_ids?: string[];
}

export interface ApplyOptimizationRequest {
  optimization_id: string;
  resume_version_id?: string | null;
  decisions?: Array<{ change_id: string; action: "accept" | "reject" }>;
  bulk_action?: "accept_all" | "reject_all";
}

export interface ApplyOptimizationResponse {
  resume_id: string;
  optimization_id: string;
  accepted_change_ids: string[];
  rejected_change_ids: string[];
  updated_content: Record<string, unknown>;
  message: string;
  analysis_stale: boolean;
  match_stale: boolean;
  reanalyze_recommended: boolean;
}

export type ChangeDecision = "accept" | "reject" | "pending";

export const REVIEW_SECTIONS = [
  { key: "professional_summary", label: "Professional summary" },
  { key: "skills", label: "Skills" },
  { key: "experience", label: "Experience" },
  { key: "projects", label: "Projects" },
  { key: "education", label: "Education" },
  { key: "achievements", label: "Achievements" },
] as const;
