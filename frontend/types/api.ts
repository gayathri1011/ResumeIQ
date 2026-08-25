export interface ApiErrorDetail {
  code: string;
  message: string;
  details?: string | null;
}

export interface ApiErrorResponse {
  error: ApiErrorDetail;
}

export interface HealthResponse {
  status: string;
  environment: string;
  version: string;
}
