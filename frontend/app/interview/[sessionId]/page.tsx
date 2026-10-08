"use client";

import { useParams } from "next/navigation";
import { AppShell } from "@/components/layout/AppShell";
import { InterviewSessionView } from "@/features/interview/InterviewSessionView";

export default function InterviewSessionRoute() {
  const params = useParams();
  const sessionId = Array.isArray(params?.sessionId)
    ? params.sessionId[0]
    : (params?.sessionId as string);

  if (!sessionId) return null;

  return (
    <AppShell>
      <InterviewSessionView sessionId={sessionId} />
    </AppShell>
  );
}
