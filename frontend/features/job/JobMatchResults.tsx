"use client";

import { Check, Circle, Loader2, X } from "lucide-react";

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
import { ScoreCountUp } from "@/features/dashboard/ScoreCountUp";
import type { JobMatchResult } from "@/types/match";
import { MATCH_BREAKDOWN_LABELS } from "@/types/match";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

interface JobMatchResultsProps {
  result: JobMatchResult;
}

export function JobMatchResults({ result }: JobMatchResultsProps) {
  const chartData = Object.entries(result.breakdown).map(([key, value]) => ({
    key,
    label: MATCH_BREAKDOWN_LABELS[key as keyof typeof MATCH_BREAKDOWN_LABELS],
    score: value,
  }));

  return (
    <div className="space-y-4">
      {result.cached ? (
        <Alert variant="info">
          Cached match — resume and job description unchanged since last computation.
        </Alert>
      ) : null}

      <Card>
        <CardHeader>
          <CardTitle>Job match score</CardTitle>
          <CardDescription>
            {result.job_title}
            {result.company ? ` at ${result.company}` : ""}
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col items-center gap-6 sm:flex-row sm:items-start">
          <CircularScore score={result.match_score} size={140} strokeWidth={10} />
          <div className="flex-1 space-y-2 text-center sm:text-left">
            <p className="text-4xl font-semibold">
              <ScoreCountUp value={result.match_score} />
              <span className="text-lg text-muted-foreground"> / 100</span>
            </p>
            <p className="text-sm text-muted-foreground">{result.summary}</p>
            {result.semantic_score !== null && (
              <p className="text-xs text-muted-foreground">
                Semantic similarity: {Math.round(result.semantic_score)} / 100
              </p>
            )}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Match breakdown</CardTitle>
        </CardHeader>
        <CardContent className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData} margin={{ top: 8, right: 8, left: -16, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
              <XAxis dataKey="label" tick={{ fontSize: 11 }} interval={0} angle={-20} textAnchor="end" height={60} />
              <YAxis domain={[0, 100]} tick={{ fontSize: 12 }} />
              <Tooltip formatter={(value: number) => [`${value} / 100`, "Score"]} />
              <Bar dataKey="score" fill="hsl(var(--primary))" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base text-emerald-700 dark:text-emerald-400">
              <Check className="h-4 w-4" />
              Matched skills
            </CardTitle>
          </CardHeader>
          <CardContent>
            {result.matched_skills.length === 0 ? (
              <p className="text-sm text-muted-foreground">No overlapping skills identified.</p>
            ) : (
              <div className="flex flex-wrap gap-2">
                {result.matched_skills.map((skill) => (
                  <Badge key={skill} variant="secondary">
                    {skill}
                  </Badge>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base text-amber-700 dark:text-amber-400">
              <X className="h-4 w-4" />
              Missing skills
            </CardTitle>
          </CardHeader>
          <CardContent>
            {result.missing_skills.length === 0 ? (
              <p className="text-sm text-muted-foreground">No missing required skills flagged.</p>
            ) : (
              <div className="flex flex-wrap gap-2">
                {result.missing_skills.map((skill) => (
                  <Badge key={skill} variant="outline">
                    {skill}
                  </Badge>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Important missing keywords</CardTitle>
          <CardDescription>
            Domain terms and methodologies from the JD not reflected in your resume
          </CardDescription>
        </CardHeader>
        <CardContent>
          {result.missing_keywords.length === 0 ? (
            <p className="text-sm text-muted-foreground">No missing keywords flagged.</p>
          ) : (
            <div className="flex flex-wrap gap-2">
              {result.missing_keywords.map((keyword) => (
                <Badge key={keyword} variant="outline">
                  {keyword}
                </Badge>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
