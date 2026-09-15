export interface RecruiterSnapshot {
  target_role: string;
  experience: string;
  strongest_skills: string[];
  domain: string;
  differentiator: string;
}

export interface RecruiterScore {
  key: string;
  label: string;
  score: number;
  explanation: string;
}

export interface RecruiterAttention {
  area: string;
  visibility: number;
  rationale: string;
}

export interface RecruiterEvidence {
  title: string;
  evidence: string;
}

export interface RecruiterRisk {
  issue: string;
  reason: string;
}

export interface RecruiterImprovement {
  action: string;
  reason: string;
}

export interface RecruiterLens {
  lens_id: string;
  resume_id: string;
  resume_version_id: string | null;
  cached: boolean;
  recruiter_snapshot: RecruiterSnapshot;
  first_impression: string;
  clarity: string;
  scores: RecruiterScore[];
  attention_map: RecruiterAttention[];
  visible_strengths: RecruiterEvidence[];
  potentially_missed: RecruiterEvidence[];
  risks: RecruiterRisk[];
  improvements: RecruiterImprovement[];
  current_positioning: string;
  recommended_positioning: string;
  limitations: string[];
  analyzed_at: string;
  prompt_version: string;
}
