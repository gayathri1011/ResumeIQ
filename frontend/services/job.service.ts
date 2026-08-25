import { apiClient } from "@/lib/api-client";
import type { AnalyzeJobRequest, JobAnalysisResult, JobListItem } from "@/types/job";

export async function analyzeJobDescription(
  payload: AnalyzeJobRequest,
): Promise<JobAnalysisResult> {
  return apiClient.post<JobAnalysisResult>("/api/v1/jobs/analyze", payload);
}

export async function getJobDescription(jobId: string): Promise<JobAnalysisResult> {
  return apiClient.get<JobAnalysisResult>(`/api/v1/jobs/${jobId}`);
}

export async function listJobDescriptions(): Promise<JobListItem[]> {
  return apiClient.get<JobListItem[]>("/api/v1/jobs");
}
