import { apiClient } from "@/lib/api-client";
import type { RecruiterLens } from "@/types/recruiter-lens";

export async function analyzeRecruiterLens(
  resumeId: string,
  versionId?: string | null,
): Promise<RecruiterLens> {
  const params = versionId ? `?versionId=${versionId}` : "";
  return apiClient.post<RecruiterLens>(
    `/api/v1/resumes/${resumeId}/recruiter-lens${params}`,
  );
}
