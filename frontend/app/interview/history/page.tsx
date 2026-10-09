import { Suspense } from "react";
import { AppShell } from "@/components/layout/AppShell";
import { FeatureSkeleton } from "@/components/ui/feature-skeleton";
import { InterviewHistoryView } from "@/features/interview/InterviewHistoryView";

export default function InterviewHistoryPage() {
  return (
    <AppShell>
      <Suspense fallback={<FeatureSkeleton cardHeight="h-96" />}>
        <InterviewHistoryView />
      </Suspense>
    </AppShell>
  );
}
