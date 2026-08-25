"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { CircularScore } from "@/features/dashboard/CircularScore";
import { WhyThisScoreDialog } from "@/features/dashboard/WhyThisScoreDialog";
import type { LatestJobMatchSummary, ResumeAnalysis } from "@/types/analysis";
import { CATEGORY_CONFIG } from "@/types/analysis";
import {
  getCategoryScore,
  getDimensionExplanation,
  scoreColor,
} from "@/features/dashboard/utils";
import { cn } from "@/lib/utils";

interface CategoryScoreGridProps {
  analysis: ResumeAnalysis;
  jobMatch?: LatestJobMatchSummary | null;
  resumeId?: string;
}

export function CategoryScoreGrid({ analysis, jobMatch, resumeId }: CategoryScoreGridProps) {
  const [dialogScope, setDialogScope] = useState<{
    key: string;
    label: string;
    score: number | null;
    explanation: string | null;
  } | null>(null);

  return (
    <>
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
        {CATEGORY_CONFIG.map((category) => {
          const isJobMatch = category.key === "job_match";
          const isPlaceholder = isJobMatch && !jobMatch;
          const score = isJobMatch
            ? (jobMatch?.match_score ?? null)
            : getCategoryScore(analysis, category.key);
          const explanation = isJobMatch
            ? (jobMatch?.summary ?? null)
            : category.dimensionKey
              ? getDimensionExplanation(analysis, category.dimensionKey)
              : null;

          return (
            <Card key={category.key}>
              <CardHeader className="flex flex-row items-start justify-between space-y-0 pb-2">
                <div>
                  <CardTitle className="text-sm font-medium">
                    {category.label}
                  </CardTitle>
                  {isPlaceholder && (
                    <CardDescription className="mt-1">
                      Not matched yet
                    </CardDescription>
                  )}
                  {isJobMatch && jobMatch?.job_title && (
                    <CardDescription className="mt-1">
                      vs {jobMatch.job_title}
                      {jobMatch.company ? ` · ${jobMatch.company}` : ""}
                    </CardDescription>
                  )}
                </div>
                {!isPlaceholder && score !== null && (
                  <div className="score-orb !p-1.5">
                    <CircularScore score={score} size={56} strokeWidth={5} />
                  </div>
                )}
              </CardHeader>
              <CardContent className="space-y-3">
                {isPlaceholder ? (
                  <p className="text-sm text-muted-foreground">
                    Analyze a job description and run a match from the{" "}
                    <a href="/jobs/analyze" className="underline">
                      job analyzer
                    </a>{" "}
                    to see your fit score here.
                  </p>
                ) : (
                  <>
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-muted-foreground">Score</span>
                      <span className={cn("font-semibold tabular-nums", score !== null ? scoreColor(score) : "")}>
                        {score !== null ? `${score} / 100` : "—"}
                      </span>
                    </div>
                    {explanation && (
                      <p className="line-clamp-2 text-xs text-muted-foreground">
                        {explanation}
                      </p>
                    )}
                    {!isJobMatch && (
                      <Button
                        variant="ghost"
                        size="sm"
                        className="h-8 px-2 text-xs"
                        onClick={() =>
                          setDialogScope({
                            key: category.key,
                            label: category.label,
                            score,
                            explanation,
                          })
                        }
                      >
                        Why this score?
                      </Button>
                    )}
                  </>
                )}
              </CardContent>
            </Card>
          );
        })}
      </div>

      {dialogScope && (
        <WhyThisScoreDialog
          open
          onOpenChange={(open) => !open && setDialogScope(null)}
          scopeKey={dialogScope.key}
          title={dialogScope.label}
          score={dialogScope.score}
          explanation={dialogScope.explanation}
          analysis={analysis}
          resumeId={resumeId}
        />
      )}
    </>
  );
}
