import { apiClient } from "@/lib/api-client";
import type {
  ImproveBulletRequest,
  ImproveBulletResponse,
  ReplaceBulletRequest,
  ReplaceBulletResponse,
  ResumeBulletItem,
} from "@/types/bullet";

export async function listResumeBullets(
  resumeId: string,
  versionId?: string | null,
): Promise<ResumeBulletItem[]> {
  const params = versionId ? `?versionId=${versionId}` : "";
  return apiClient.get<ResumeBulletItem[]>(
    `/api/v1/bullets/resume/${resumeId}${params}`,
  );
}

export async function improveBullet(
  body: ImproveBulletRequest,
): Promise<ImproveBulletResponse> {
  return apiClient.post<ImproveBulletResponse>("/api/v1/bullets/improve", body);
}

export async function replaceBullet(
  body: ReplaceBulletRequest,
): Promise<ReplaceBulletResponse> {
  return apiClient.post<ReplaceBulletResponse>("/api/v1/bullets/replace", body);
}
