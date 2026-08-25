import { Suspense } from "react";

import { OptimizationReview } from "@/features/optimization/OptimizationReview";
import { FeatureSkeleton } from "@/components/ui/feature-skeleton";

export default function OptimizationReviewPage() {
  return (
    <Suspense fallback={<FeatureSkeleton cardHeight="h-72" />}>
      <OptimizationReview />
    </Suspense>
  );
}
