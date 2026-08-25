"use client";

import { BookOpen, Target } from "lucide-react";

import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { CircularScore } from "@/features/dashboard/CircularScore";
import type { SkillGapResult, SkillGapPriority } from "@/types/skill-gap";
import { PRIORITY_LABELS } from "@/types/skill-gap";

function priorityVariant(priority: SkillGapPriority): "high" | "medium" | "low" {
  return priority;
}

interface SkillGapPanelProps {
  result: SkillGapResult;
}

export function SkillGapPanel({ result }: SkillGapPanelProps) {
  return (
    <div className="space-y-4">
      {result.cached ? (
        <Alert variant="info">Skill gap analysis loaded from cache — match data unchanged.</Alert>
      ) : null}

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Target className="h-4 w-4" />
            Skill gap analysis
          </CardTitle>
          <CardDescription>
            {result.target_role}
            {result.company ? ` at ${result.company}` : ""} · Match score{" "}
            {result.match_score} / 100
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col items-center gap-4 sm:flex-row sm:items-start">
          <CircularScore
            score={Math.round(result.skill_coverage_percent)}
            size={120}
            strokeWidth={10}
            label="Coverage"
          />
          <div className="space-y-2 text-sm text-muted-foreground">
            <p>
              <span className="font-medium text-foreground">
                {result.skill_coverage_percent}%
              </span>{" "}
              skill coverage
            </p>
            <p>{result.coverage_meta.formula}</p>
            <p>
              Required skills count fully (1.0 weight); preferred skills,
              tools, and technologies count at half weight (0.5).
            </p>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Missing skills (prioritized)</CardTitle>
          <CardDescription>
            Grounded in your job match and the JD&apos;s required vs preferred skills
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {result.missing_skills.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              No skill gaps identified — your resume covers the JD skill requirements.
            </p>
          ) : (
            result.missing_skills.map((item) => (
              <div key={item.skill} className="rounded-lg border p-4 space-y-2">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-medium">{item.skill}</span>
                  <Badge variant={priorityVariant(item.priority)}>
                    {PRIORITY_LABELS[item.priority]}
                  </Badge>
                  <span className="text-xs text-muted-foreground">({item.source})</span>
                </div>
                <p className="text-sm text-muted-foreground">{item.why_it_matters}</p>
              </div>
            ))
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <BookOpen className="h-4 w-4" />
            Suggested learning roadmap
          </CardTitle>
          <CardDescription>
            Ordered sequence based on missing skills and reasonable prerequisites
          </CardDescription>
        </CardHeader>
        <CardContent>
          {result.learning_roadmap.length === 0 ? (
            <p className="text-sm text-muted-foreground">No roadmap needed.</p>
          ) : (
            <ol className="space-y-3">
              {result.learning_roadmap.map((step, index) => (
                <li key={`${step.skill}-${index}`} className="flex gap-3">
                  <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-muted text-xs font-semibold">
                    {index + 1}
                  </span>
                  <div>
                    <p className="font-medium">{step.skill}</p>
                    <p className="text-sm text-muted-foreground">{step.rationale}</p>
                  </div>
                </li>
              ))}
            </ol>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
