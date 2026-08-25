import { apiClient } from "@/lib/api-client";
import type {
  ApplyOptimizationRequest,
  ApplyOptimizationResponse,
  OptimizationProposal,
} from "@/types/optimize";

export async function optimizeResume(
  resumeId: string,
  body: {
    target_role: string;
    job_id?: string | null;
    resume_version_id?: string | null;
  },
): Promise<OptimizationProposal> {
  return apiClient.post<OptimizationProposal>(
    `/api/v1/resumes/${resumeId}/optimize`,
    body,
  );
}

export async function getLatestOptimization(
  resumeId: string,
  versionId?: string | null,
): Promise<OptimizationProposal | null> {
  const params = versionId ? `?versionId=${versionId}` : "";
  return apiClient.get<OptimizationProposal | null>(
    `/api/v1/resumes/${resumeId}/optimization/latest${params}`,
  );
}

export async function applyOptimization(
  resumeId: string,
  body: ApplyOptimizationRequest,
): Promise<ApplyOptimizationResponse> {
  return apiClient.post<ApplyOptimizationResponse>(
    `/api/v1/resumes/${resumeId}/optimization/apply`,
    body,
  );
}
