export interface TrajectoryFactor {
  key: string;
  label: string;
  score: number;
  weight: number;
  explanation: string;
}

export interface TrajectoryPath {
  role: string;
  timeframe: string;
  readiness_score: number;
  summary: string;
  matched_skills: string[];
  skill_gaps: string[];
  proof_gaps: string[];
  factors: TrajectoryFactor[];
  next_steps: string[];
}

export interface CareerTrajectory {
  trajectory_id: string;
  resume_id: string;
  resume_version_id: string | null;
  cached: boolean;
  current_profile: string;
  profile_summary: string;
  paths: TrajectoryPath[];
  limitations: string[];
  analyzed_at: string | null;
  prompt_version: string;
}
