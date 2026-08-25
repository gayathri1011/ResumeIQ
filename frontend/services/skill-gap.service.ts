import { apiClient } from "@/lib/api-client";
import type { SkillGapResult } from "@/types/skill-gap";

export async function getJobSkillGap(
  jobId: string,
  resumeId: string,
  resumeVersionId?: string | null,
): Promise<SkillGapResult> {
  const params = new URLSearchParams({ resume_id: resumeId });
  if (resumeVersionId) {
    params.set("resume_version_id", resumeVersionId);
  }
  return apiClient.get<SkillGapResult>(
    `/api/v1/jobs/${jobId}/skill-gap?${params.toString()}`,
  );
}
