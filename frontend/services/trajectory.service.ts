import { apiClient } from "@/lib/api-client";
import type { CareerTrajectory } from "@/types/trajectory";

export async function analyzeCareerTrajectory(
  resumeId: string,
  versionId?: string | null,
): Promise<CareerTrajectory> {
  const params = versionId ? `?versionId=${versionId}` : "";
  return apiClient.post<CareerTrajectory>(
    `/api/v1/resumes/${resumeId}/trajectory${params}`,
  );
}
