"use client";

import { Check, CircleAlert, X } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogBody,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import type { JobMatchResult } from "@/types/match";
import { MATCH_BREAKDOWN_LABELS } from "@/types/match";

interface JobMatchWhyScoreDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  result: JobMatchResult;
}

function scoreInterpretation(score: number): string {
  if (score >= 80) return "This is a strong match based on the current resume-to-job comparison.";
  if (score >= 60) return "This is a moderate match with relevant alignment and some meaningful gaps.";
  if (score >= 40) return "This is a partial match; several requirements are not clearly supported by the resume.";
  return "This is a limited match because the resume does not clearly support many of the job requirements.";
}

export function JobMatchWhyScoreDialog({
  open,
  onOpenChange,
  result,
}: JobMatchWhyScoreDialogProps) {
  const explanationsByCategory = new Map(
    result.explanations.map((explanation) => [explanation.category, explanation.summary]),
  );

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent onClose={() => onOpenChange(false)} className="max-w-xl">
        <DialogHeader>
          <DialogTitle>Why this score?</DialogTitle>
          <DialogDescription>
            Match score: <span className="font-medium">{result.match_score} / 100</span>
          </DialogDescription>
        </DialogHeader>
        <DialogBody className="space-y-5">
          <div className="space-y-2">
            <p className="text-sm font-medium">{scoreInterpretation(result.match_score)}</p>
            <p className="text-sm leading-relaxed text-muted-foreground">{result.summary}</p>
          </div>

          <div className="space-y-3">
            <h3 className="text-sm font-semibold">Score breakdown</h3>
            {Object.entries(result.breakdown).map(([key, score]) => (
              <div key={key} className="space-y-1.5">
                <div className="flex items-center justify-between text-sm">
                  <span>{MATCH_BREAKDOWN_LABELS[key as keyof typeof MATCH_BREAKDOWN_LABELS]}</span>
                  <span className="font-semibold tabular-nums">{score} / 100</span>
                </div>
                <div className="h-2 overflow-hidden rounded-full bg-muted">
                  <div className="h-full rounded-full bg-primary" style={{ width: `${score}%` }} />
                </div>
                {explanationsByCategory.has(key) ? (
                  <p className="text-xs leading-relaxed text-muted-foreground">
                    {explanationsByCategory.get(key)}
                  </p>
                ) : null}
              </div>
            ))}
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <section className="space-y-3">
              <h3 className="flex items-center gap-2 text-sm font-semibold text-emerald-700 dark:text-emerald-400">
                <Check className="h-4 w-4" />
                Strong matches
              </h3>
              {result.matched_skills.length === 0 ? (
                <p className="text-sm text-muted-foreground">No overlapping skills were identified.</p>
              ) : (
                <ul className="space-y-2">
                  {result.matched_skills.map((skill) => (
                    <li key={skill} className="flex gap-2 text-sm">
                      <Check className="mt-0.5 h-4 w-4 shrink-0 text-emerald-600" />
                      <span>{skill} is present in the resume and matched the job analysis.</span>
                    </li>
                  ))}
                </ul>
              )}
            </section>

            <section className="space-y-3">
              <h3 className="flex items-center gap-2 text-sm font-semibold text-amber-700 dark:text-amber-400">
                <X className="h-4 w-4" />
                Missing requirements
              </h3>
              {result.missing_skills.length === 0 && result.missing_keywords.length === 0 ? (
                <p className="text-sm text-muted-foreground">No missing skills or keywords were flagged.</p>
              ) : (
                <ul className="space-y-2">
                  {[...result.missing_skills, ...result.missing_keywords].map((item, index) => (
                    <li key={`${item}-${index}`} className="flex gap-2 text-sm">
                      <X className="mt-0.5 h-4 w-4 shrink-0 text-amber-600" />
                      <span>{item} was not clearly identified in the resume-to-job comparison.</span>
                    </li>
                  ))}
                </ul>
              )}
            </section>
          </div>

          {result.explanations.length === 0 ? (
            <div className="flex gap-2 rounded-lg border border-dashed p-4 text-sm text-muted-foreground">
              <CircleAlert className="mt-0.5 h-4 w-4 shrink-0" />
              The match breakdown is available, but no additional category explanation was returned.
            </div>
          ) : null}

          <div className="space-y-2">
            <h3 className="text-sm font-semibold">Overall reasoning</h3>
            <p className="text-sm leading-relaxed text-muted-foreground">
              {result.summary || "The score reflects the weighted match breakdown shown above."}
            </p>
            <Badge variant="info">Based on this resume and job description</Badge>
          </div>
        </DialogBody>
      </DialogContent>
    </Dialog>
  );
}
