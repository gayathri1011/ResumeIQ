import { ApiClientError, apiClient } from "@/lib/api-client";
import type {
  CareerGrowthPlan,
  CreateGrowthPlanRequest,
  ProjectRecommendation,
  ReadinessOverview,
  SyncInterviewResult,
  UpdateMilestoneStatusRequest,
} from "@/types/growth";

export async function createGrowthPlan(
  payload: CreateGrowthPlanRequest,
): Promise<CareerGrowthPlan> {
  return apiClient.post<CareerGrowthPlan>("/api/v1/growth/plans", payload);
}

export async function getLatestGrowthPlan(
  targetRole?: string,
): Promise<CareerGrowthPlan | null> {
  const query = targetRole ? `?target_role=${encodeURIComponent(targetRole)}` : "";
  try {
    return await apiClient.get<CareerGrowthPlan | null>(`/api/v1/growth/plans/latest${query}`);
  } catch (err: unknown) {
    if (err instanceof ApiClientError && (err.status === 404 || err.status === 204)) {
      return null;
    }
    throw err;
  }
}

export async function getGrowthPlan(planId: string): Promise<CareerGrowthPlan> {
  return apiClient.get<CareerGrowthPlan>(`/api/v1/growth/plans/${planId}`);
}

export async function getReadinessOverview(
  planId: string,
): Promise<ReadinessOverview> {
  return apiClient.get<ReadinessOverview>(`/api/v1/growth/plans/${planId}/readiness`);
}

export async function updateMilestoneStatus(
  planId: string,
  itemId: string,
  payload: UpdateMilestoneStatusRequest,
): Promise<CareerGrowthPlan> {
  return apiClient.patch<CareerGrowthPlan>(
    `/api/v1/growth/plans/${planId}/roadmap/${itemId}`,
    payload,
  );
}

export async function getProjectRecommendations(
  planId: string,
): Promise<ProjectRecommendation[]> {
  return apiClient.get<ProjectRecommendation[]>(
    `/api/v1/growth/plans/${planId}/projects`,
  );
}

export async function refreshGrowthPlan(
  planId: string,
): Promise<CareerGrowthPlan> {
  return apiClient.post<CareerGrowthPlan>(
    `/api/v1/growth/plans/${planId}/refresh`,
    {},
  );
}

export async function syncInterviewToPlan(
  planId: string,
  sessionId: string,
): Promise<SyncInterviewResult> {
  return apiClient.post<SyncInterviewResult>(
    `/api/v1/growth/plans/${planId}/sync-interview/${sessionId}`,
    {},
  );
}
