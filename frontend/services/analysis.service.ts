import { apiClient } from "@/lib/api-client";
import type { ResumeAnalysis, ResumeDetail, ResumeListItem } from "@/types/analysis";

export async function listResumes(): Promise<ResumeListItem[]> {
  return apiClient.get<ResumeListItem[]>("/api/v1/resumes");
}

export async function getResume(
  resumeId: string,
  versionId?: string | null,
): Promise<ResumeDetail> {
  const params = versionId ? `?versionId=${versionId}` : "";
  return apiClient.get<ResumeDetail>(`/api/v1/resumes/${resumeId}${params}`);
}

export async function analyzeResume(
  resumeId: string,
  versionId?: string | null,
): Promise<ResumeAnalysis> {
  const params = versionId ? `?versionId=${versionId}` : "";
  return apiClient.post<ResumeAnalysis>(
    `/api/v1/resumes/${resumeId}/analyze${params}`,
  );
}
