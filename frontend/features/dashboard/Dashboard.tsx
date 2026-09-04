"use client";

import dynamic from "next/dynamic";
import { useState } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import { Loader2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { AppShell } from "@/components/layout/AppShell";
import { PageHeader } from "@/components/layout/PageHeader";
import { CategoryScoreGrid } from "@/features/dashboard/CategoryScoreGrid";
import { CircularScore } from "@/features/dashboard/CircularScore";
import { DashboardEmpty } from "@/features/dashboard/DashboardEmpty";
import { DashboardError } from "@/features/dashboard/DashboardError";
import { DashboardSkeleton } from "@/features/dashboard/DashboardSkeleton";
import { QuickActions } from "@/features/dashboard/QuickActions";
import { ScoreCountUp } from "@/features/dashboard/ScoreCountUp";
import { TargetRoleField } from "@/features/dashboard/TargetRoleField";
import { useDashboard } from "@/features/dashboard/useDashboard";
import { getGreeting } from "@/features/dashboard/utils";
import { WhyThisScoreDialog } from "@/features/dashboard/WhyThisScoreDialog";
import { DownloadPdfButton } from "@/features/versions/DownloadPdfButton";
import { useAuth } from "@/features/auth/AuthProvider";
import { formControlClass } from "@/lib/design";

const CategoryBreakdownChart = dynamic(
  () =>
    import("@/features/dashboard/CategoryBreakdownChart").then(
      (module) => module.CategoryBreakdownChart,
    ),
  {
    ssr: false,
    loading: () => (
      <div className="surface-3d h-64 animate-pulse" aria-hidden="true" />
    ),
  },
);

export function Dashboard() {
  const {
    status,
    errorMessage,
    data,
    isAnalyzing,
    load,
    selectResume,
    runAnalysis,
  } = useDashboard();
  const { user } = useAuth();
  const [showOverallWhy, setShowOverallWhy] = useState(false);

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

  const { resume, resumes, selectedResumeId } = data;
  const analysis = resume.latest_analysis;
  const jobMatch = resume.latest_job_match ?? null;
  const overallScore = analysis?.overall_score ?? null;
  const displayName =
    resume.original_filename?.replace(/\.[^.]+$/, "") ?? resume.title;
  const needsAnalysis =
    Boolean(resume.reanalyze_recommended) || status === "no_analysis";

  return (
    <AppShell>
      <motion.div
        className="space-y-6"
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.2, ease: "easeOut" }}
      >
        <PageHeader
          title={`${getGreeting()}${user?.full_name ? `, ${user.full_name}` : ""}`}
          description="Resume health overview and actionable insights"
          actions={
            resume.active_version_id ? (
              <DownloadPdfButton
                resumeId={resume.id}
                versionId={resume.active_version_id}
                versionLabel={resume.active_version_label}
              />
            ) : null
          }
        />

        {needsAnalysis ? (
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base">
                {status === "no_analysis"
                  ? "Ready for analysis"
                  : "Refresh your scores"}
              </CardTitle>
              <CardDescription>
                {status === "no_analysis"
                  ? `${displayName} is uploaded. Run analysis to unlock health scores and insights.`
                  : "Resume content changed after the last analysis. Refresh to keep scores accurate."}
              </CardDescription>
            </CardHeader>
            <CardContent className="flex flex-wrap gap-2">
              <Button onClick={() => void runAnalysis()} disabled={isAnalyzing}>
                {isAnalyzing ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                ) : null}
                {status === "no_analysis" ? "Run analysis" : "Re-analyze"}
              </Button>
              {status === "no_analysis" ? (
                <Button variant="outline" asChild>
                  <Link href="/resumes/upload">Upload another</Link>
                </Button>
              ) : null}
              {errorMessage ? (
                <p className="w-full text-sm text-destructive">{errorMessage}</p>
              ) : null}
            </CardContent>
          </Card>
        ) : null}

        <div className="grid gap-6 lg:grid-cols-3">
          <Card className="lg:col-span-2">
            <CardHeader>
              <CardTitle>Resume health</CardTitle>
              <CardDescription>
                Overall score from your latest AI analysis
              </CardDescription>
            </CardHeader>
            <CardContent className="flex flex-col items-center gap-6 sm:flex-row sm:items-start">
              <div className="score-orb">
                <CircularScore
                  score={overallScore}
                  size={160}
                  strokeWidth={12}
                />
              </div>
              <div className="flex-1 space-y-3 text-center sm:text-left">
                {overallScore !== null ? (
                  <p className="text-4xl font-semibold tabular-nums">
                    <ScoreCountUp value={overallScore} />
                    <span className="text-lg text-muted-foreground"> / 100</span>
                  </p>
                ) : (
                  <p className="text-2xl font-medium text-muted-foreground">
                    Not analyzed yet
                  </p>
                )}
                {analysis?.summary ? (
                  <p className="text-sm leading-relaxed text-muted-foreground">
                    {analysis.summary}
                  </p>
                ) : null}
                {analysis ? (
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-9 px-2"
                    onClick={() => setShowOverallWhy(true)}
                  >
                    Why this score?
                  </Button>
                ) : null}
              </div>
            </CardContent>
          </Card>

          <div className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Recent resume</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3 text-sm">
                <div>
                  <p className="font-medium">{displayName}</p>
                </div>
                {resumes.length > 1 ? (
                  <div className="space-y-2">
                    <Label htmlFor="resume-select">Switch resume</Label>
                    <select
                      id="resume-select"
                      className={formControlClass}
                      value={selectedResumeId}
                      onChange={(event) => selectResume(event.target.value)}
                    >
                      {resumes.map((item) => (
                        <option key={item.id} value={item.id}>
                          {item.original_filename ?? item.title}
                        </option>
                      ))}
                    </select>
                  </div>
                ) : null}
                <div className="border-t border-border/60 pt-3">
                  <p className="text-xs text-muted-foreground">Latest score</p>
                  <p className="font-medium tabular-nums">
                    {overallScore !== null ? `${overallScore} / 100` : "—"}
                  </p>
                </div>
              </CardContent>
            </Card>

            <TargetRoleField resumeId={resume.id} />
          </div>
        </div>

        {analysis ? (
          <>
            <CategoryBreakdownChart analysis={analysis} jobMatch={jobMatch} />
            <CategoryScoreGrid
              analysis={analysis}
              jobMatch={jobMatch}
              resumeId={resume.id}
            />
          </>
        ) : null}

        <QuickActions
          resumeId={resume.id}
          versionId={resume.active_version_id}
        />

        {analysis ? (
          <WhyThisScoreDialog
            open={showOverallWhy}
            onOpenChange={setShowOverallWhy}
            scopeKey="overall"
            title="Overall resume health"
            score={overallScore}
            explanation={analysis.summary}
            analysis={analysis}
            resumeId={resume.id}
          />
        ) : null}
      </motion.div>
    </AppShell>
  );
}
