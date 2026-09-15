"use client";

import { Check, X } from "lucide-react";
import { motion } from "framer-motion";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogBody,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  fixActionLabel,
  getIssuesForScope,
} from "@/features/dashboard/utils";
import type { LatestJobMatchSummary, ResumeAnalysis } from "@/types/analysis";
import { MATCH_BREAKDOWN_LABELS } from "@/types/match";
import { normalizeSeverity } from "@/types/analysis";

interface WhyThisScoreDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  scopeKey: string;
  title: string;
  score: number | null;
  explanation: string | null;
  analysis: ResumeAnalysis;
  jobMatch?: LatestJobMatchSummary | null;
}

export function WhyThisScoreDialog({
  open,
  onOpenChange,
  scopeKey,
  title,
  score,
  explanation,
  analysis,
  jobMatch,
}: WhyThisScoreDialogProps) {
  const issues = getIssuesForScope(analysis.issues, scopeKey);
  const summary =
    scopeKey === "job_match"
      ? jobMatch?.summary ?? explanation ?? analysis.summary
      : scopeKey === "overall"
        ? analysis.summary
        : explanation ?? analysis.summary;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent onClose={() => onOpenChange(false)} className="max-w-xl">
        <DialogHeader>
          <DialogTitle>Why this score? — {title}</DialogTitle>
          <DialogDescription>
            {score !== null ? (
              <>
                Score: <span className="font-medium">{score} / 100</span>
              </>
            ) : (
              "No score available for this category yet."
            )}
          </DialogDescription>
        </DialogHeader>
        <DialogBody className="space-y-4">
          <p className="text-sm leading-relaxed text-muted-foreground">{summary}</p>

          {scopeKey === "job_match" && jobMatch ? (
            <div className="space-y-5">
              {jobMatch.breakdown ? (
                <section className="space-y-3">
                  <h3 className="text-sm font-semibold">Match breakdown</h3>
                  {Object.entries(jobMatch.breakdown).map(([key, value]) => (
                    <div key={key} className="flex items-center justify-between gap-3 text-sm">
                      <span>{MATCH_BREAKDOWN_LABELS[key as keyof typeof MATCH_BREAKDOWN_LABELS]}</span>
                      <span className="font-semibold tabular-nums">{value ?? 0} / 100</span>
                    </div>
                  ))}
                </section>
              ) : null}

              <div className="grid gap-4 sm:grid-cols-2">
                <section className="space-y-3">
                  <h3 className="flex items-center gap-2 text-sm font-semibold text-emerald-700 dark:text-emerald-400">
                    <Check className="h-4 w-4" />
                    Strong matches
                  </h3>
                  {jobMatch.matched_skills?.length ? (
                    <ul className="space-y-2 text-sm text-muted-foreground">
                      {jobMatch.matched_skills.map((skill) => (
                        <li key={skill} className="flex gap-2">
                          <Check className="mt-0.5 h-4 w-4 shrink-0 text-emerald-600" />
                          <span>{skill} is present in the resume and matched the job analysis.</span>
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="text-sm text-muted-foreground">No overlapping skills were identified.</p>
                  )}
                </section>

                <section className="space-y-3">
                  <h3 className="flex items-center gap-2 text-sm font-semibold text-amber-700 dark:text-amber-400">
                    <X className="h-4 w-4" />
                    Missing requirements
                  </h3>
                  {(jobMatch.missing_skills?.length || jobMatch.missing_keywords?.length) ? (
                    <ul className="space-y-2 text-sm text-muted-foreground">
                      {[...(jobMatch.missing_skills ?? []), ...(jobMatch.missing_keywords ?? [])].map((item, index) => (
                        <li key={`${item}-${index}`} className="flex gap-2">
                          <X className="mt-0.5 h-4 w-4 shrink-0 text-amber-600" />
                          <span>{item} was not clearly identified in the resume-to-job comparison.</span>
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="text-sm text-muted-foreground">No missing skills or keywords were flagged.</p>
                  )}
                </section>
              </div>

              {jobMatch.explanations?.length ? (
                <section className="space-y-3">
                  <h3 className="text-sm font-semibold">Overall reasoning</h3>
                  <ul className="space-y-2 text-sm text-muted-foreground">
                    {jobMatch.explanations.map((item) => (
                      <li key={item.category}>
                        <span className="font-medium text-foreground">{item.category}: </span>
                        {item.summary}
                      </li>
                    ))}
                  </ul>
                </section>
              ) : null}
            </div>
          ) : issues.length === 0 ? (
            <p className="rounded-lg border border-dashed p-4 text-sm text-muted-foreground">
              No specific issues were flagged for this area in the latest analysis.
            </p>
          ) : (
            <ul className="space-y-3">
              {issues.map((issue, index) => {
                const severity = normalizeSeverity(issue.severity);
                return (
                  <motion.li
                    key={`${issue.title}-${index}`}
                    initial={{ opacity: 0, y: 6 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: index * 0.04, duration: 0.25 }}
                    className="space-y-2 rounded-lg border p-4"
                  >
                    <div className="flex flex-wrap items-center gap-2">
                      <Badge variant={severity}>{severity.toUpperCase()}</Badge>
                      <span className="text-sm font-medium">{issue.title}</span>
                    </div>
                    <p className="text-sm text-muted-foreground">
                      {issue.description}
                    </p>
                    {issue.suggested_fix && (
                      <p className="text-sm">
                        <span className="font-medium">Suggested fix: </span>
                        {issue.suggested_fix}
                      </p>
                    )}
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() =>
                        window.alert(
                          `${fixActionLabel(issue.category)} — this guided fix flow ships in a later phase.`,
                        )
                      }
                    >
                      Fix this
                    </Button>
                  </motion.li>
                );
              })}
            </ul>
          )}
        </DialogBody>
      </DialogContent>
    </Dialog>
  );
}
