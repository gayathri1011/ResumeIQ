"use client";

import { AppShell } from "@/components/layout/AppShell";
import { PageHeader } from "@/components/layout/PageHeader";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { DashboardError } from "@/features/dashboard/DashboardError";
import { DashboardSkeleton } from "@/features/dashboard/DashboardSkeleton";
import { useDashboard } from "@/features/dashboard/useDashboard";
import { RecruiterLens } from "@/features/recruiter-lens/RecruiterLens";
import Link from "next/link";

export function RecruiterLensPage() {
  const { status, errorMessage, data, load } = useDashboard({
    routePath: "/recruiter-lens",
  });

  if (status === "loading") {
    return <AppShell><DashboardSkeleton /></AppShell>;
  }

  if (status === "error") {
    return <DashboardError message={errorMessage ?? "Unknown error"} onRetry={() => void load()} />;
  }

  if (status === "empty" || !data) {
    return (
      <AppShell className="flex min-h-[calc(100vh-3.5rem)] items-center justify-center">
        <Card className="w-full max-w-lg">
          <CardHeader className="text-center">
            <CardTitle>Upload your resume first</CardTitle>
            <CardDescription>
              Upload your resume to see how recruiters are likely to perceive your profile in the first few seconds.
            </CardDescription>
          </CardHeader>
          <CardContent className="flex justify-center">
            <Button asChild><Link href="/resumes/upload">Upload resume</Link></Button>
          </CardContent>
        </Card>
      </AppShell>
    );
  }

  const query = new URLSearchParams({ resumeId: data.resume.id });
  if (data.resume.active_version_id) query.set("versionId", data.resume.active_version_id);

  return (
    <AppShell>
      <div className="mx-auto w-full max-w-5xl space-y-6">
        <PageHeader
          title="Recruiter 10-Second Lens"
          description="See what a recruiter is likely to notice in the first few seconds."
          backHref={`/dashboard?${query.toString()}`}
        />
        <RecruiterLens
          resumeId={data.resume.id}
          versionId={data.resume.active_version_id}
        />
      </div>
    </AppShell>
  );
}
