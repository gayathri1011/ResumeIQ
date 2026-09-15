import { Suspense } from "react";

import { FeatureSkeleton } from "@/components/ui/feature-skeleton";
import { RecruiterLensPage } from "@/features/recruiter-lens/RecruiterLensPage";

export default function Page() {
  return (
    <Suspense fallback={<FeatureSkeleton cardHeight="h-96" cards={2} />}>
      <RecruiterLensPage />
    </Suspense>
  );
}
