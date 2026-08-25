export interface ResumeUploadResponse {
  id: string;
  title: string;
  original_filename: string | null;
  file_size_bytes: number;
  mime_type: string | null;
  sections_found: string[];
  sections_missing: string[];
  created_at: string;
}

export type UploadStage =
  | "idle"
  | "uploading"
  | "extracting"
  | "understanding"
  | "analyzing"
  | "generating_insights"
  | "success"
  | "error";

export const UPLOAD_STAGES: { key: UploadStage; label: string }[] = [
  { key: "uploading", label: "Uploading" },
  { key: "extracting", label: "Extracting" },
  { key: "understanding", label: "Understanding" },
  { key: "analyzing", label: "Analyzing" },
  { key: "generating_insights", label: "Generating Insights" },
];

export const SECTION_LABELS: Record<string, string> = {
  personal_information: "Personal Information",
  professional_summary: "Professional Summary",
  education: "Education",
  experience: "Experience",
  projects: "Projects",
  skills: "Skills",
  certifications: "Certifications",
  achievements: "Achievements",
  links: "Links",
};
