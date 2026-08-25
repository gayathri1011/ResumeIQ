import { API_BASE_URL } from "@/lib/constants";
import { ApiClientError } from "@/lib/api-client";
import { getUserFriendlyErrorMessage } from "@/lib/error-messages";
import { clearAccessToken, getAccessToken } from "@/lib/auth-storage";

function parseFilename(contentDisposition: string | null): string | null {
  if (!contentDisposition) return null;
  const match = /filename="?([^";]+)"?/i.exec(contentDisposition);
  return match?.[1] ?? null;
}

function slugifyLabel(label: string | null | undefined): string {
  const base = (label ?? "resume").trim() || "resume";
  return base
    .toLowerCase()
    .replace(/[^\w\s-]/g, "")
    .replace(/[\s_-]+/g, "-")
    .replace(/^-+|-+$/g, "");
}

export async function downloadBlob(blob: Blob, filename: string): Promise<void> {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}

export async function generateVersionPdf(
  resumeId: string,
  versionId: string,
  versionLabel?: string | null,
): Promise<void> {
  let response: Response;
  try {
    response = await fetch(
      `${API_BASE_URL}/api/v1/resumes/${resumeId}/versions/${versionId}/generate`,
      {
        method: "POST",
        headers: {
          ...(getAccessToken() ? { Authorization: `Bearer ${getAccessToken()}` } : {}),
        },
      },
    );
  } catch {
    throw new ApiClientError(
      getUserFriendlyErrorMessage({ code: "network_error", message: "" }),
      0,
      "network_error",
    );
  }

  if (response.status === 401) {
    clearAccessToken();
    window.location.href = "/login";
    throw new ApiClientError("Authentication required.", 401, "unauthorized");
  }

  if (!response.ok) {
    try {
      const data = (await response.json()) as {
        error?: { message?: string; code?: string };
      };
      if (data.error?.message) {
        throw new ApiClientError(
          data.error.message,
          response.status,
          data.error.code ?? "http_error",
        );
      }
    } catch (error) {
      if (error instanceof ApiClientError) {
        throw error;
      }
    }
    throw new ApiClientError(
      "Failed to generate resume PDF.",
      response.status,
      "pdf_generation_failed",
    );
  }

  const blob = await response.blob();
  if (!blob.size || blob.type !== "application/pdf") {
    throw new ApiClientError(
      "The server returned an invalid PDF file.",
      response.status,
      "pdf_generation_failed",
    );
  }

  const filename =
    parseFilename(response.headers.get("Content-Disposition")) ??
    `${slugifyLabel(versionLabel)}.pdf`;

  await downloadBlob(blob, filename);
}
