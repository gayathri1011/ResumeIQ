export interface ResumeBulletItem {
  section: "experience" | "projects";
  entry_index: number;
  bullet_index: number;
  entry_title: string | null;
  organization: string | null;
  text: string;
}

export interface ImproveBulletRequest {
  bullet_text: string;
  resume_id?: string;
  resume_version_id?: string | null;
  target_role?: string | null;
  regenerate?: boolean;
  previous_improved_text?: string | null;
}

export interface ImproveBulletResponse {
  original_text: string;
  improved_text: string;
  changes_summary: string;
  metric_placeholder_used: boolean;
  suggested_metric_prompt: string | null;
  regenerate: boolean;
  prompt_version: string;
}

export interface ReplaceBulletRequest {
  resume_id: string;
  resume_version_id?: string | null;
  section: "experience" | "projects";
  entry_index: number;
  bullet_index: number;
  improved_text: string;
}

export interface ReplaceBulletResponse {
  resume_id: string;
  section: string;
  entry_index: number;
  bullet_index: number;
  updated_text: string;
  message: string;
}

export type BulletImproveStage = "idle" | "improving" | "done" | "error";
