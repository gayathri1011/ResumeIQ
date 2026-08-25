"use client";

import { motion } from "framer-motion";
import Link from "next/link";
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
import type { ResumeAnalysis } from "@/types/analysis";
import { normalizeSeverity } from "@/types/analysis";

interface WhyThisScoreDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  scopeKey: string;
  title: string;
  score: number | null;
  explanation: string | null;
  analysis: ResumeAnalysis;
  resumeId?: string;
}

export function WhyThisScoreDialog({
  open,
  onOpenChange,
  scopeKey,
  title,
  score,
  explanation,
  analysis,
  resumeId,
}: WhyThisScoreDialogProps) {
  const issues = getIssuesForScope(analysis.issues, scopeKey);
  const summary =
    scopeKey === "overall" ? analysis.summary : explanation ?? analysis.summary;

  const isBulletIssue = (category: string) => {
    const key = category.toLowerCase();
    return key.includes("experience") || key.includes("project");
  };

  const bulletImproverHref = resumeId
    ? `/bullets/improve?resumeId=${resumeId}`
    : "/bullets/improve";

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

          {issues.length === 0 ? (
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
                    {isBulletIssue(issue.category) ? (
                      <Button variant="outline" size="sm" asChild>
                        <Link href={bulletImproverHref}>{fixActionLabel(issue.category)}</Link>
                      </Button>
                    ) : (
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
                    )}
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
