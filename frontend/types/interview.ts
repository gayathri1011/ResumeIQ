export type InterviewDifficulty = "junior" | "mid" | "senior" | "lead";

export type InterviewType = "technical" | "behavioral" | "mixed" | "system_design";

export type InterviewStatus = "in_progress" | "completed" | "abandoned";

export interface CreateInterviewSessionRequest {
  target_role: string;
  difficulty?: InterviewDifficulty;
  interview_type?: InterviewType;
  resume_id?: string | null;
  resume_version_id?: string | null;
  job_description_id?: string | null;
  job_description_text?: string | null;
  estimated_question_count?: number;
  focus_areas?: string[];
  focus_skills?: string[];
}

export interface InterviewTurn {
  turn_index: number;
  question: string;
  category: string;
  difficulty: string;
  skill_tag: string;
  skill_tags: string[];
  user_answer?: string | null;
  turn_score?: number | null;
  evaluation?: {
    score: number;
    dimension_scores: Record<string, number>;
    strengths: string[];
    missing_points: string[];
    feedback: string;
    next_question_direction: string;
    resume_claim_status: string;
    skill_tags: string[];
  } | null;
  is_follow_up: boolean;
  answered_at?: string | null;
}

export interface TurnEvaluation {
  turn_index: number;
  score: number;
  dimension_scores: Record<string, number>;
  strengths: string[];
  missing_points: string[];
  feedback: string;
  next_question_direction: string;
  resume_claim_status: string;
  skill_tags: string[];
  is_complete: boolean;
  next_turn?: InterviewTurn | null;
}

export interface TestedClaim {
  claim: string;
  status: "validated" | "weak" | "unverified" | "n/a";
  evidence: string;
}

export interface InterviewReport {
  session_id: string;
  target_role: string;
  overall_score: number;
  readiness_status: string;
  summary: string;
  category_scores: Record<string, number>;
  strong_areas: string[];
  weak_areas: string[];
  resume_claims_tested: TestedClaim[];
  actionable_recommendations: string[];
  ordered_practice_areas: string[];
  ordered_next_practice_areas?: string[];
  skill_scores: Record<string, number>;
  skill_evaluations?: Record<string, number>;
  turns_evaluated: number;
  completed_at?: string | null;
}

export interface InterviewSession {
  id: string;
  user_id: string;
  resume_id?: string | null;
  job_description_id?: string | null;
  target_role: string;
  difficulty: InterviewDifficulty;
  interview_type: InterviewType;
  status: InterviewStatus;
  plan?: Record<string, any> | null;
  current_turn_index: number;
  turns: InterviewTurn[];
  current_question?: string | null;
  overall_score?: number | null;
  report?: InterviewReport | null;
  started_at?: string | null;
  completed_at?: string | null;
  created_at: string;
}

export interface InterviewSessionListItem {
  id: string;
  target_role: string;
  difficulty: string;
  status: string;
  overall_score: number | null;
  turns_count: number;
  total_turns?: number;
  answered_turns?: number;
  created_at: string;
  completed_at?: string | null;
  top_strengths: string[];
  main_strengths?: string[];
  primary_gaps: string[];
  main_weaknesses?: string[];
  readiness_status: string | null;
}
