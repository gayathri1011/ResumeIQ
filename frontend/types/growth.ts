export type EvidenceClass = "evidence-backed" | "inferred" | "unverified" | "missing";
export type SkillPriority = "high" | "medium" | "low";
export type SkillImportance = "critical" | "important" | "beneficial";
export type SkillLevel = "none" | "beginner" | "competent" | "advanced" | "expert";
export type MilestoneStatus = "not_started" | "in_progress" | "completed";
export type EvidenceSourceType = "interview" | "project_evidence" | "verified_evidence" | "self_reported";

export interface SkillGap {
  skill: string;
  required_level: SkillLevel | string;
  current_level: SkillLevel | string;
  has_skill: boolean;
  evidence: string[];
  evidence_strength: "strong" | "moderate" | "weak" | "none" | string;
  evidence_class: EvidenceClass;
  importance: SkillImportance | string;
  gap: "none" | "small" | "medium" | "large" | string;
  priority: SkillPriority;
  status: "missing" | "in_progress" | "verified" | string;
  gap_type: "missing_capability" | "proof_gap" | string;
  why_it_matters: string;
  target_competency: string;
  verified_in_interview: boolean;
  latest_interview_score?: number | null;
  evidence_count: number;
}

export interface RoadmapMilestone {
  milestone_id: string;
  title: string;
  skill: string;
  why_it_matters: string;
  current_level: string;
  target_level: string;
  priority: SkillPriority;
  estimated_effort: string;
  prerequisites: string[];
  recommended_action: string;
  practical_exercise: string;
  linked_project?: string | null;
  skills_addressed: string[];
  deliverable: string;
  status: MilestoneStatus;
  completed_at?: string | null;
  evidence_type?: string | null;
  notes?: string | null;
}

export interface RoadmapPhase {
  phase_number: number;
  name: string;
  duration_weeks: number;
  focus_skills: string[];
  milestones: RoadmapMilestone[];
  learning_objectives: string[];
}

export interface ProjectRecommendation {
  project_id: string;
  title: string;
  description: string;
  why_this_project: string;
  gaps_addressed: string[];
  targeted_skills: string[];
  suggested_technologies: string[];
  difficulty: "beginner" | "intermediate" | "advanced" | string;
  architecture_overview: string;
  what_to_implement: string;
  key_deliverables: string[];
  resume_evidence: string;
  resume_bullet_preview: string;
}

export interface EvidenceEvent {
  event_id: string;
  source_type: EvidenceSourceType | string;
  source_id: string;
  idempotency_key: string;
  skill: string;
  score: number;
  weight: number;
  notes: string;
  recorded_at: string;
}

export interface ChangeLog {
  change_id: string;
  timestamp: string;
  change_type: string;
  message: string;
  affected_skills: string[];
}

export interface CareerGrowthPlan {
  id: string;
  user_id: string;
  resume_id?: string | null;
  resume_version_id?: string | null;
  target_role: string;
  target_company?: string | null;
  readiness_score: number;
  status: string;
  summary?: string | null;
  skill_gaps: SkillGap[];
  roadmap_phases: RoadmapPhase[];
  project_recommendations: ProjectRecommendation[];
  evidence_events: EvidenceEvent[];
  change_logs: ChangeLog[];
  last_evaluated_at?: string | null;
  created_at: string;
}

export interface ReadinessOverview {
  target_role: string;
  overall_readiness_score: number;
  evidence_classes_summary: Record<string, number>;
  priorities_summary: Record<string, number>;
  skill_gaps: SkillGap[];
  weighting_policy: Record<string, number>;
}

export interface CreateGrowthPlanRequest {
  resume_id?: string | null;
  resume_version_id?: string | null;
  target_role: string;
  target_company?: string | null;
}

export interface UpdateMilestoneStatusRequest {
  status: MilestoneStatus;
  evidence_type?: string;
  notes?: string | null;
}

export interface SyncInterviewResult {
  plan_id: string;
  session_id: string;
  events_added: number;
  updated_readiness_score: number;
  affected_skills: string[];
  message: string;
  already_synced: boolean;
}
