"use client";

import { useState } from "react";
import { Eye, Lightbulb, Loader2, RefreshCw, TriangleAlert } from "lucide-react";

import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { getUserFriendlyErrorMessage } from "@/lib/error-messages";
import { analyzeRecruiterLens } from "@/services/recruiter-lens.service";
import type { RecruiterLens } from "@/types/recruiter-lens";

interface RecruiterLensProps {
  resumeId: string;
  versionId?: string | null;
}

function EvidenceList({
  items,
  emptyLabel,
}: {
  items: Array<{ title: string; evidence: string }>;
  emptyLabel: string;
}) {
  if (items.length === 0) {
    return <p className="text-sm text-muted-foreground">{emptyLabel}</p>;
  }
  return (
    <ul className="space-y-3">
      {items.map((item) => (
        <li key={`${item.title}-${item.evidence}`} className="space-y-1">
          <p className="text-sm font-medium">{item.title}</p>
          <p className="text-sm leading-relaxed text-muted-foreground">{item.evidence}</p>
        </li>
      ))}
    </ul>
  );
}

function RecruiterSnapshot({ result }: { result: RecruiterLens }) {
  const snapshot = result.recruiter_snapshot;
  const fields = [
    ["Target role", snapshot.target_role],
    ["Experience", snapshot.experience],
    ["Domain", snapshot.domain],
    ["Differentiator", snapshot.differentiator],
  ];

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <Eye className="h-4 w-4" />
          What a recruiter sees first
        </CardTitle>
        <CardDescription>Estimated from the resume structure and content, not real eye-tracking data.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid gap-3 sm:grid-cols-2">
          {fields.map(([label, value]) => (
            <div key={label} className="rounded-xl border border-border/60 bg-muted/25 p-3">
              <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">{label}</p>
              <p className="mt-1 text-sm leading-relaxed">{value}</p>
            </div>
          ))}
        </div>
        <div className="space-y-2">
          <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Strongest skills</p>
          {snapshot.strongest_skills.length > 0 ? (
            <div className="flex flex-wrap gap-2">
              {snapshot.strongest_skills.map((skill) => <Badge key={skill} variant="secondary">{skill}</Badge>)}
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">Not clearly indicated.</p>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

function VisibilityScores({ result }: { result: RecruiterLens }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">10-second visibility scores</CardTitle>
        <CardDescription>Deterministic estimates based on section presence, repetition, and scannable evidence.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {result.scores.map((score) => (
          <div key={score.key} className="space-y-1.5">
            <div className="flex items-center justify-between gap-3 text-sm">
              <span className="font-medium">{score.label}</span>
              <span className="font-semibold tabular-nums">{score.score}%</span>
            </div>
            <div className="h-2 overflow-hidden rounded-full bg-muted" aria-label={`${score.label}: ${score.score} out of 100`}>
              <div className="h-full rounded-full bg-primary transition-all" style={{ width: `${score.score}%` }} />
            </div>
            <p className="text-xs leading-relaxed text-muted-foreground">{score.explanation}</p>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}

function AttentionMap({ result }: { result: RecruiterLens }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Recruiter attention map</CardTitle>
        <CardDescription>Estimated recruiter attention based on resume structure and content.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        {result.attention_map.map((item) => (
          <div key={item.area} className="space-y-1.5">
            <div className="flex items-center justify-between text-sm">
              <span>{item.area}</span>
              <span className="font-semibold tabular-nums">{item.visibility}%</span>
            </div>
            <div className="h-2 overflow-hidden rounded-full bg-muted">
              <div className="h-full rounded-full bg-primary/75" style={{ width: `${item.visibility}%` }} />
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}

export function RecruiterLens({ resumeId, versionId }: RecruiterLensProps) {
  const [result, setResult] = useState<RecruiterLens | null>(null);
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const runAnalysis = async () => {
    setLoading(true);
    setErrorMessage(null);
    try {
      setResult(await analyzeRecruiterLens(resumeId, versionId));
    } catch (error) {
      setErrorMessage(getUserFriendlyErrorMessage(error, "Could not analyze the recruiter first impression. Please try again."));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <CardTitle className="flex items-center gap-2"><span className="icon-orb h-9 w-9"><Eye className="h-4 w-4" /></span>Recruiter 10-Second Lens</CardTitle>
            <CardDescription className="mt-2">See what a recruiter is likely to notice in the first few seconds.</CardDescription>
          </div>
          <Button variant="outline" onClick={() => void runAnalysis()} disabled={loading}>
            {loading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : result ? <RefreshCw className="mr-2 h-4 w-4" /> : <Eye className="mr-2 h-4 w-4" />}
            {loading ? "Scanning resume" : result ? "Refresh scan" : "Run 10-second scan"}
          </Button>
        </CardHeader>
        <CardContent>
          {errorMessage ? <Alert variant="error">{errorMessage}</Alert> : null}
          {!result && !errorMessage ? (
            <div className="flex items-center gap-3 rounded-xl border border-dashed border-border p-5 text-sm text-muted-foreground">
              <Eye className="h-5 w-5 shrink-0 text-primary" />
              This scan uses your existing parsed resume to identify what is immediately clear, what may be missed, and how to sharpen the first impression.
            </div>
          ) : null}
        </CardContent>
      </Card>

      {result ? (
        <>
          {result.cached ? <Alert variant="info">Showing a cached scan because this resume version has not changed.</Alert> : null}
          <RecruiterSnapshot result={result} />
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Recruiter first impression</CardTitle>
              <CardDescription>{result.clarity}</CardDescription>
            </CardHeader>
            <CardContent>
              <p className="text-sm leading-relaxed text-muted-foreground">{result.first_impression}</p>
            </CardContent>
          </Card>
          <div className="grid gap-4 lg:grid-cols-2">
            <VisibilityScores result={result} />
            <AttentionMap result={result} />
          </div>
          <div className="grid gap-4 lg:grid-cols-2">
            <Card>
              <CardHeader><CardTitle className="flex items-center gap-2 text-base text-emerald-700 dark:text-emerald-400"><Lightbulb className="h-4 w-4" />Recruiter-visible strengths</CardTitle></CardHeader>
              <CardContent><EvidenceList items={result.visible_strengths} emptyLabel="No distinct strengths were clearly surfaced." /></CardContent>
            </Card>
            <Card>
              <CardHeader><CardTitle className="flex items-center gap-2 text-base text-amber-700 dark:text-amber-400"><TriangleAlert className="h-4 w-4" />What a recruiter may miss</CardTitle></CardHeader>
              <CardContent><EvidenceList items={result.potentially_missed} emptyLabel="No specific buried evidence was identified." /></CardContent>
            </Card>
          </div>
          <div className="grid gap-4 lg:grid-cols-2">
            <Card>
              <CardHeader><CardTitle className="text-base">First-impression risks</CardTitle></CardHeader>
              <CardContent><EvidenceList items={result.risks.map((item) => ({ title: item.issue, evidence: item.reason }))} emptyLabel="No specific first-impression risks were identified." /></CardContent>
            </Card>
            <Card>
              <CardHeader><CardTitle className="text-base">Make your resume clearer in 10 seconds</CardTitle></CardHeader>
              <CardContent><EvidenceList items={result.improvements.map((item) => ({ title: item.action, evidence: item.reason }))} emptyLabel="No specific improvements were identified." /></CardContent>
            </Card>
          </div>
          <Card>
            <CardHeader><CardTitle className="text-base">Positioning preview</CardTitle><CardDescription>Conceptual positioning using existing resume facts; this does not rewrite your resume.</CardDescription></CardHeader>
            <CardContent className="grid gap-4 sm:grid-cols-2">
              <div className="rounded-xl border border-border/60 p-4"><p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Current first impression</p><p className="mt-2 text-sm leading-relaxed text-muted-foreground">{result.current_positioning}</p></div>
              <div className="rounded-xl border border-primary/25 bg-primary/5 p-4"><p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Recommended positioning</p><p className="mt-2 text-sm leading-relaxed">{result.recommended_positioning}</p></div>
            </CardContent>
          </Card>
          {result.limitations.length > 0 ? <p className="text-xs leading-relaxed text-muted-foreground">Based on resume evidence only: {result.limitations.join(" ")}</p> : null}
        </>
      ) : null}
    </div>
  );
}
