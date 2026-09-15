"use client";

import { AppShell } from "@/components/layout/AppShell";
import { PageHeader } from "@/components/layout/PageHeader";
import { DashboardEmpty } from "@/features/dashboard/DashboardEmpty";
import { DashboardError } from "@/features/dashboard/DashboardError";
import { DashboardSkeleton } from "@/features/dashboard/DashboardSkeleton";
import { useDashboard } from "@/features/dashboard/useDashboard";
import { CareerTrajectory } from "@/features/trajectory/CareerTrajectory";

export function CareerTrajectoryPage() {
  const { status, errorMessage, data, load } = useDashboard({
    routePath: "/career-trajectory",
  });

  if (status === "loading") {
    return (
      <AppShell>
        <DashboardSkeleton />
      </AppShell>
    );
  }

  if (status === "empty") {
    return <DashboardEmpty />;
  }

  if (status === "error") {
    return (
      <DashboardError
        message={errorMessage ?? "Unknown error"}
        onRetry={() => void load()}
      />
    );
  }

  if (!data) {
    return (
      <AppShell>
        <DashboardSkeleton />
      </AppShell>
    );
  }

  const { resume } = data;
  const dashboardQuery = new URLSearchParams({ resumeId: resume.id });
  if (resume.active_version_id) {
    dashboardQuery.set("versionId", resume.active_version_id);
  }

  return (
    <AppShell>
      <div className="mx-auto w-full max-w-5xl space-y-6">
        <PageHeader
          title="Career trajectory"
          description="Discover where your career can go next based on the evidence in your resume."
          backHref={`/dashboard?${dashboardQuery.toString()}`}
        />
        <CareerTrajectory
          resumeId={resume.id}
          versionId={resume.active_version_id}
          available={Boolean(resume.latest_analysis)}
        />
      </div>
    </AppShell>
  );
}
