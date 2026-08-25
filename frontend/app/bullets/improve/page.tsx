import { Suspense } from "react";

import { BulletImprover } from "@/features/bullet/BulletImprover";
import { FeatureSkeleton } from "@/components/ui/feature-skeleton";

export default function BulletImprovePage() {
  return (
    <Suspense fallback={<FeatureSkeleton cardHeight="h-96" />}>
      <BulletImprover />
    </Suspense>
  );
}
