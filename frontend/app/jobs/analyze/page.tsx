import { Suspense } from "react";

import { JobAnalyzer } from "@/features/job/JobAnalyzer";
import { FeatureSkeleton } from "@/components/ui/feature-skeleton";

export default function AnalyzeJobPage() {
  return (
    <Suspense fallback={<FeatureSkeleton cardHeight="h-96" />}>
      <JobAnalyzer />
    </Suspense>
  );
}
