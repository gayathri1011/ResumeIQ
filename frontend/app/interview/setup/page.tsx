import { Suspense } from "react";
import { AppShell } from "@/components/layout/AppShell";
import { FeatureSkeleton } from "@/components/ui/feature-skeleton";
import { InterviewSetup } from "@/features/interview/InterviewSetup";

export default function InterviewSetupPage() {
  return (
    <AppShell>
      <Suspense fallback={<FeatureSkeleton cardHeight="h-96" />}>
        <InterviewSetup />
      </Suspense>
    </AppShell>
  );
}
