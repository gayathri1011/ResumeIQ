"use client";

import { useParams } from "next/navigation";
import { AppShell } from "@/components/layout/AppShell";
import { InterviewReportView } from "@/features/interview/InterviewReportView";

export default function InterviewReportRoute() {
  const params = useParams();
  const sessionId = Array.isArray(params?.sessionId)
    ? params.sessionId[0]
    : (params?.sessionId as string);

  if (!sessionId) return null;

  return (
    <AppShell>
      <InterviewReportView sessionId={sessionId} />
    </AppShell>
  );
}
