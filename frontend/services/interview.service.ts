import { apiClient } from "@/lib/api-client";
import type {
  CreateInterviewSessionRequest,
  InterviewReport,
  InterviewSession,
  InterviewSessionListItem,
  TurnEvaluation,
} from "@/types/interview";

export async function createInterviewSession(
  payload: CreateInterviewSessionRequest,
): Promise<InterviewSession> {
  return apiClient.post<InterviewSession>("/api/v1/interviews/sessions", payload);
}

export async function getInterviewSession(sessionId: string): Promise<InterviewSession> {
  return apiClient.get<InterviewSession>(`/api/v1/interviews/sessions/${sessionId}`);
}

export async function listInterviewSessions(
  limit = 20,
  offset = 0,
): Promise<InterviewSessionListItem[]> {
  return apiClient.get<InterviewSessionListItem[]>(
    `/api/v1/interviews/sessions?limit=${limit}&offset=${offset}`,
  );
}

export async function submitTurnAnswer(
  sessionId: string,
  turnIndex: number,
  answer: string,
): Promise<TurnEvaluation> {
  return apiClient.post<TurnEvaluation>(
    `/api/v1/interviews/sessions/${sessionId}/turns/${turnIndex}/answer`,
    { answer },
  );
}

export async function endInterviewSession(sessionId: string): Promise<InterviewReport> {
  return apiClient.post<InterviewReport>(`/api/v1/interviews/sessions/${sessionId}/end`, {});
}

export async function getInterviewReport(sessionId: string): Promise<InterviewReport> {
  return apiClient.get<InterviewReport>(`/api/v1/interviews/sessions/${sessionId}/report`);
}
