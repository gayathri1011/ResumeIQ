import { API_BASE_URL } from "@/lib/constants";

import type { ApiErrorResponse } from "@/types/api";

import { clearAccessToken, getAccessToken } from "@/lib/auth-storage";

import { getUserFriendlyErrorMessage } from "@/lib/error-messages";



export class ApiClientError extends Error {

  constructor(

    message: string,

    public readonly status: number,

    public readonly code: string,

    public readonly details?: string | null,

  ) {

    super(message);

    this.name = "ApiClientError";

  }

}



type RequestOptions = Omit<RequestInit, "body"> & {

  body?: unknown;

};



function buildUrl(path: string): string {

  const normalizedPath = path.startsWith("/") ? path : `/${path}`;

  return `${API_BASE_URL}${normalizedPath}`;

}



function redirectToLogin(): void {

  if (typeof window === "undefined") return;

  clearAccessToken();

  const next = encodeURIComponent(window.location.pathname + window.location.search);

  window.location.href = `/login?next=${next}`;

}



function toApiClientError(

  status: number,

  code: string,

  message: string,

  details?: string | null,

): ApiClientError {

  const friendly = getUserFriendlyErrorMessage({ code, message, details });

  return new ApiClientError(friendly, status, code, details);

}



async function parseError(response: Response): Promise<ApiClientError> {

  try {

    const data = (await response.json()) as ApiErrorResponse & {

      detail?: Array<{ loc?: unknown[]; msg?: string }>;

    };



    if (data.error) {

      return toApiClientError(

        response.status,

        data.error.code,

        data.error.message,

        data.error.details,

      );

    }



    if (Array.isArray(data.detail) && data.detail.length > 0) {
      const first = data.detail[0];
      if (first) {
        const field = (first.loc ?? [])
          .filter((part) => part !== "body" && part !== "query")
          .join(" ");
        const message = field
          ? `${field}: ${first.msg ?? "Invalid value."}`
          : String(first.msg ?? "Invalid value.");
        return toApiClientError(response.status, "validation_error", message);
      }
    }

  } catch {

    // Fall through to generic error below.

  }



  return toApiClientError(

    response.status,

    "http_error",

    `Request failed with status ${response.status}`,

  );

}



export async function apiRequest<T>(

  path: string,

  options: RequestOptions = {},

): Promise<T> {

  const { body, headers, ...rest } = options;

  const token = getAccessToken();



  let response: Response;

  try {

    response = await fetch(buildUrl(path), {

      ...rest,

      headers: {

        ...(body !== undefined ? { "Content-Type": "application/json" } : {}),

        ...(token ? { Authorization: `Bearer ${token}` } : {}),

        ...headers,

      },

      body: body !== undefined ? JSON.stringify(body) : undefined,

    });

  } catch {

    throw toApiClientError(

      0,

      "network_error",

      "Network connection lost. Check your internet connection and try again.",

    );

  }



  if (response.status === 401 && !path.startsWith("/api/v1/auth/")) {

    redirectToLogin();

    throw await parseError(response);

  }



  if (!response.ok) {

    throw await parseError(response);

  }



  if (response.status === 204) {

    return undefined as T;

  }



  return (await response.json()) as T;

}



export const apiClient = {

  get: <T>(path: string, options?: RequestOptions) =>

    apiRequest<T>(path, { ...options, method: "GET" }),



  post: <T>(path: string, body?: unknown, options?: RequestOptions) =>

    apiRequest<T>(path, { ...options, method: "POST", body }),



  put: <T>(path: string, body?: unknown, options?: RequestOptions) =>

    apiRequest<T>(path, { ...options, method: "PUT", body }),



  patch: <T>(path: string, body?: unknown, options?: RequestOptions) =>

    apiRequest<T>(path, { ...options, method: "PATCH", body }),



  delete: <T>(path: string, options?: RequestOptions) =>

    apiRequest<T>(path, { ...options, method: "DELETE" }),

};



export function uploadFormData<T>(

  path: string,

  formData: FormData,

  onProgress?: (percent: number) => void,

): Promise<T> {

  return new Promise((resolve, reject) => {

    const xhr = new XMLHttpRequest();

    xhr.open("POST", buildUrl(path));

    const token = getAccessToken();

    if (token) {

      xhr.setRequestHeader("Authorization", `Bearer ${token}`);

    }



    xhr.upload.onprogress = (event) => {

      if (event.lengthComputable && onProgress) {

        onProgress(Math.round((event.loaded / event.total) * 100));

      }

    };



    xhr.onload = () => {

      if (xhr.status === 401) {

        redirectToLogin();

        reject(toApiClientError(401, "unauthorized", "Authentication required."));

        return;

      }



      if (xhr.status >= 200 && xhr.status < 300) {

        try {

          resolve(JSON.parse(xhr.responseText) as T);

        } catch {

          reject(toApiClientError(xhr.status, "parse_error", "Invalid response from server."));

        }

        return;

      }



      try {

        const data = JSON.parse(xhr.responseText) as ApiErrorResponse;

        if (data.error) {

          reject(

            toApiClientError(

              xhr.status,

              data.error.code,

              data.error.message,

              data.error.details,

            ),

          );

          return;

        }

      } catch {

        // fall through

      }

      reject(

        toApiClientError(

          xhr.status,

          "http_error",

          `Upload failed with status ${xhr.status}`,

        ),

      );

    };



    xhr.onerror = () => {

      reject(

        toApiClientError(

          0,

          "network_error",

          "Network error during upload.",

        ),

      );

    };



    xhr.send(formData);

  });

}

