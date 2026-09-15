import { Suspense } from "react";

import { FeatureSkeleton } from "@/components/ui/feature-skeleton";
import { CareerTrajectoryPage } from "@/features/trajectory/CareerTrajectoryPage";

export default function Page() {
  return (
    <Suspense fallback={<FeatureSkeleton cardHeight="h-96" />}>
      <CareerTrajectoryPage />
    </Suspense>
  );
}
