import type { ApiClientError } from "@/lib/api-client";

const ERROR_MESSAGES: Record<string, string> = {
  unauthorized: "Please log in to continue.",
  invalid_credentials: "Invalid email or password.",
  invalid_token: "Your session is invalid. Please log in again.",
  token_expired: "Your session has expired. Please log in again.",
  email_already_registered: "An account with this email already exists.",
  validation_error: "Please check your input and try again.",
  invalid_file_type: "Only PDF, DOCX, and image files (PNG, JPG, WEBP) are supported.",
  file_too_large: "This file is too large. Please upload a smaller resume.",
  corrupted_file: "The file appears to be corrupted or unreadable.",
  empty_resume: "No readable text could be extracted from this resume.",
  extraction_failed: "We could not extract structured content from this resume.",
  resume_not_found: "Resume not found.",
  resume_version_not_found: "Resume version not found.",
  job_not_found: "Job description not found.",
  jd_empty: "Please paste a job description before analyzing.",
  jd_too_short: "The job description is too short to analyze meaningfully.",
  match_not_found: "Run job matching before viewing skill gaps.",
  ai_not_configured: "AI features are not configured. Please contact support.",
  ai_provider_error:
    "AI service is temporarily unavailable. Please try again in a moment.",
  ai_timeout: "AI analysis timed out. Please try again.",
  ai_rate_limit: "AI service is busy. Please wait a moment and try again.",
  ai_output_invalid: "AI returned an unexpected result. Please try again.",
  rate_limit_exceeded: "Too many requests. Please wait a moment and try again.",
  database_unavailable:
    "The service is temporarily unavailable. Please try again shortly.",
  database_error: "Something went wrong while saving data. Please try again.",
  database_conflict:
    "This action conflicted with another update. Please refresh and try again.",
  version_create_conflict:
    "Could not create a new version due to a concurrent update. Please try again.",
  role_transform_failed:
    "Could not generate a valid role-specific resume. Please try again.",
  version_delete_last: "You cannot delete the only remaining version.",
  version_delete_master: "The master resume version cannot be deleted.",
  pdf_generation_failed: "Could not generate the PDF. Please try again.",
  network_error:
    "Network connection lost. Check your internet connection and try again.",
  parse_error: "Received an invalid response from the server. Please try again.",
  http_error: "Something went wrong. Please try again.",
  internal_error: "Something went wrong. Please try again.",
};

const INTERNAL_PATTERNS = [
  /traceback/i,
  /\.py:\d+/i,
  /sqlalchemy/i,
  /integrityerror/i,
  /operationalerror/i,
  /exception:/i,
  /at\s+\w+\s+\(/i,
];

function looksInternal(message: string): boolean {
  return INTERNAL_PATTERNS.some((pattern) => pattern.test(message));
}

function sanitizeMessage(message: string): string {
  const trimmed = message.trim();
  if (!trimmed || looksInternal(trimmed)) {
    return ERROR_MESSAGES.internal_error ?? "Something went wrong. Please try again.";
  }
  return trimmed;
}

export function getUserFriendlyErrorMessage(
  error: unknown,
  fallback = "Something went wrong. Please try again.",
): string {
  if (error && typeof error === "object" && "code" in error && "message" in error) {
    const apiError = error as Pick<ApiClientError, "code" | "message" | "details">;
    if (ERROR_MESSAGES[apiError.code]) {
      return ERROR_MESSAGES[apiError.code]!;
    }
    return sanitizeMessage(String(apiError.message));
  }

  if (error instanceof Error) {
    return sanitizeMessage(error.message);
  }

  return fallback;
}

export function isRetryableErrorCode(code: string | undefined): boolean {
  return (
    code === "ai_provider_error" ||
    code === "ai_timeout" ||
    code === "ai_rate_limit" ||
    code === "rate_limit_exceeded" ||
    code === "database_unavailable" ||
    code === "network_error"
  );
}
