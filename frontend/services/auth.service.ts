import type { AuthResponse, LoginRequest, SignupRequest, UserProfile } from "@/types/auth";
import { apiClient } from "@/lib/api-client";
import { clearAccessToken, setAccessToken } from "@/lib/auth-storage";

export async function signup(body: SignupRequest): Promise<AuthResponse> {
  const response = await apiClient.post<AuthResponse>("/api/v1/auth/signup", body);
  setAccessToken(response.access_token);
  return response;
}

export async function login(body: LoginRequest): Promise<AuthResponse> {
  const response = await apiClient.post<AuthResponse>("/api/v1/auth/login", body);
  setAccessToken(response.access_token);
  return response;
}

export async function logout(): Promise<void> {
  try {
    await apiClient.post("/api/v1/auth/logout");
  } finally {
    clearAccessToken();
  }
}

export async function getCurrentUser(): Promise<UserProfile> {
  return apiClient.get<UserProfile>("/api/v1/auth/me");
}
