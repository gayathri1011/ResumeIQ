import { apiClient } from "@/lib/api-client";
import type { JobMatchResult, MatchJobRequest } from "@/types/match";

export async function matchJobDescription(
  jobId: string,
  payload: MatchJobRequest,
): Promise<JobMatchResult> {
  return apiClient.post<JobMatchResult>(`/api/v1/jobs/${jobId}/match`, payload);
}

export async function listResumeMatches(resumeId: string): Promise<JobMatchResult[]> {
  return apiClient.get<JobMatchResult[]>(`/api/v1/resumes/${resumeId}/matches`);
}
