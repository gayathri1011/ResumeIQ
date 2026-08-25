import { apiClient } from "@/lib/api-client";
import type { HealthResponse } from "@/types/api";

export async function checkHealth(): Promise<HealthResponse> {
  return apiClient.get<HealthResponse>("/api/v1/health");
}
