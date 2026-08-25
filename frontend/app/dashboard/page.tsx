import { Suspense } from "react";

import { Dashboard } from "@/features/dashboard/Dashboard";
import { DashboardSkeletonPage } from "@/features/dashboard/DashboardSkeleton";

export default function DashboardPage() {
  return (
    <Suspense fallback={<DashboardSkeletonPage />}>
      <Dashboard />
    </Suspense>
  );
}
