import { Suspense } from "react";
import { AppShell } from "@/components/layout/AppShell";
import { FeatureSkeleton } from "@/components/ui/feature-skeleton";
import { CareerGrowthDashboard } from "@/features/growth/CareerGrowthDashboard";

export default function GrowthPage() {
  return (
    <AppShell>
      <Suspense fallback={<FeatureSkeleton cardHeight="h-96" />}>
        <CareerGrowthDashboard />
      </Suspense>
    </AppShell>
  );
}
