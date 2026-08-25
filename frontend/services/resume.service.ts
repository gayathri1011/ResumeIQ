import { uploadFormData } from "@/lib/api-client";
import type { ResumeUploadResponse } from "@/types/resume";

export async function uploadResume(
  file: File,
  onProgress?: (percent: number) => void,
): Promise<ResumeUploadResponse> {
  const formData = new FormData();
  formData.append("file", file);
  return uploadFormData<ResumeUploadResponse>("/api/v1/resumes/upload", formData, onProgress);
}
