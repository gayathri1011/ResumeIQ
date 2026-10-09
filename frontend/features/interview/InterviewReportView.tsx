"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  AlertCircle,
  ArrowRight,
  BookOpen,
  CheckCircle2,
  FileCheck,
  History,
  Layers,
  ListOrdered,
  Loader2,
  RotateCcw,
  Sparkles,
  TrendingUp,
} from "lucide-react";

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
import { getInterviewReport, getInterviewSession } from "@/services/interview.service";
import type { InterviewReport, InterviewSession } from "@/types/interview";

interface InterviewReportViewProps {
  sessionId: string;
}

function getScoreWord(score: number): string {
  if (score >= 75) return "Strong";
  if (score >= 50) return "Getting there";
  return "Needs work";
}

const READINESS_BADGE_MAP: Record<string, { label: string; variant: "secondary" | "outline" | "high" }> = {
  interview_ready: { label: "Interview ready", variant: "secondary" },
  strong_fit: { label: "Strong fit", variant: "secondary" },
  needs_preparation: { label: "Needs practice", variant: "outline" },
  significant_gaps: { label: "Skills to learn", variant: "high" },
  needs_work: { label: "Needs work", variant: "high" },
  progressing: { label: "Progressing", variant: "outline" },
};

function ScoreDonut({ score }: { score: number }) {
  const radius = 60;
  const stroke = 9;
  const normalizedRadius = radius - stroke;
  const circumference = normalizedRadius * 2 * Math.PI;
  const safeScore = Math.min(100, Math.max(0, score));
  const strokeDashoffset = circumference - (safeScore / 100) * circumference;

  let strokeColor = "#ef4444"; // red
  let textColor = "text-red-600 dark:text-red-400";
  let statusText = "Needs work";

  if (safeScore >= 75) {
    strokeColor = "#10b981"; // green
    textColor = "text-emerald-600 dark:text-emerald-400";
    statusText = "Strong";
  } else if (safeScore >= 50) {
    strokeColor = "#f59e0b"; // amber
    textColor = "text-amber-600 dark:text-amber-400";
    statusText = "Getting there";
  }

  return (
    <div className="flex flex-col items-center">
      <div className="relative flex items-center justify-center">
        <svg height={radius * 2} width={radius * 2} className="transform -rotate-90">
          <circle
            stroke="currentColor"
            fill="transparent"
            strokeWidth={stroke}
            className="text-muted/20"
            r={normalizedRadius}
            cx={radius}
            cy={radius}
          />
          <circle
            stroke={strokeColor}
            fill="transparent"
            strokeWidth={stroke}
            strokeDasharray={`${circumference} ${circumference}`}
            style={{ strokeDashoffset, transition: "stroke-dashoffset 0.8s ease" }}
            strokeLinecap="round"
            r={normalizedRadius}
            cx={radius}
            cy={radius}
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-2xl sm:text-3xl font-extrabold tracking-tight text-foreground font-mono">
            {safeScore}%
          </span>
        </div>
      </div>
      <span className={`text-xs font-semibold mt-2 ${textColor}`}>{statusText}</span>
    </div>
  );
}

export function InterviewReportView({ sessionId }: InterviewReportViewProps) {
  const [report, setReport] = useState<InterviewReport | null>(null);
  const [session, setSession] = useState<InterviewSession | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isRetrying, setIsRetrying] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const fetchReportData = async (attempt = 0) => {
    try {
      if (attempt === 0) {
        setIsLoading(true);
        setIsRetrying(false);
      } else {
        setIsRetrying(true);
      }
      setErrorMessage(null);

      const rep = await getInterviewReport(sessionId);
      let sess: InterviewSession | null = null;
      try {
        sess = await getInterviewSession(sessionId);
      } catch {
        // non-blocking
      }

      setReport(rep);
      setSession(sess);
      setIsLoading(false);
      setIsRetrying(false);
    } catch (err: any) {
      if (attempt < 3) {
        setIsRetrying(true);
        setTimeout(() => {
          void fetchReportData(attempt + 1);
        }, 2000);
      } else {
        setIsLoading(false);
        setIsRetrying(false);
        setErrorMessage(getUserFriendlyErrorMessage(err, "Something went wrong. Please try again."));
      }
    }
  };

  useEffect(() => {
    void fetchReportData(0);
  }, [sessionId]);

  if (isLoading || isRetrying) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[50vh] space-y-4">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
        <div className="text-center space-y-1">
          <p className="text-base font-semibold text-foreground">Preparing your report...</p>
          <p className="text-xs text-muted-foreground">Synthesizing answers and calculating feedback</p>
        </div>
      </div>
    );
  }

  if (errorMessage || !report) {
    return (
      <div className="mx-auto max-w-lg py-12 space-y-4">
        <Alert variant="error" className="flex items-start gap-3">
          <AlertCircle className="h-5 w-5 shrink-0 mt-0.5" />
          <div className="space-y-1">
            <p className="font-semibold text-sm">Could not load report</p>
            <p className="text-xs text-muted-foreground">
              {errorMessage || "Something went wrong. Please try again."}
            </p>
          </div>
        </Alert>
        <div className="flex justify-center gap-3">
          <Button variant="default" onClick={() => void fetchReportData(0)}>
            Retry
          </Button>
          <Link href="/interview/history">
            <Button variant="outline">View Past Interviews</Button>
          </Link>
          <Link href="/interview/setup">
            <Button variant="outline">Start New Interview</Button>
          </Link>
        </div>
      </div>
    );
  }

  const badgeInfo = READINESS_BADGE_MAP[report.readiness_status] || {
    label: report.readiness_status.replace("_", " "),
    variant: "outline",
  };

  const categoryEntries = Object.entries(report.category_scores || {});
  const answeredTurns = session?.turns?.filter((t) => t.user_answer !== null) || [];

  return (
    <div className="mx-auto w-full max-w-4xl space-y-8 pb-16">
      {/* Header & Quick Actions */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-border/50 pb-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-foreground mt-1">
            Interview Feedback: {report.target_role}
          </h1>
          <p className="text-xs text-muted-foreground mt-1">
            Completed on {new Date(report.completed_at || Date.now()).toLocaleDateString()} &bull; {report.turns_evaluated} question(s) answered
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Link href="/interview/history">
            <Button variant="outline" size="sm" className="gap-1.5">
              <History className="h-4 w-4" />
              History
            </Button>
          </Link>
          <Link href={`/interview/setup?role=${encodeURIComponent(report.target_role)}`}>
            <Button size="sm" className="gap-1.5">
              <RotateCcw className="h-4 w-4" />
              Practice Again
            </Button>
          </Link>
        </div>
      </div>

      {/* Hero Overall Score Card with SVG Donut */}
      <Card className="border-border/60 shadow-sm overflow-hidden">
        <CardContent className="p-6 sm:p-8 flex flex-col sm:flex-row items-center gap-8">
          <div className="shrink-0 flex flex-col items-center">
            <ScoreDonut score={report.overall_score} />
            <Badge variant={badgeInfo.variant} className="mt-2 capitalize text-xs">
              {badgeInfo.label}
            </Badge>
          </div>

          <div className="space-y-3 flex-1 text-center sm:text-left">
            <div>
              <h2 className="text-lg font-semibold text-foreground">Overall Summary</h2>
              <p className="text-sm text-muted-foreground mt-1 leading-relaxed whitespace-pre-wrap">
                {report.summary}
              </p>
            </div>

            <div className="flex flex-wrap gap-2 pt-1 justify-center sm:justify-start">
              {Object.entries(report.skill_scores || report.skill_evaluations || {}).slice(0, 4).map(([skill, score]) => (
                <Badge key={skill} variant="outline" className="text-xs font-mono">
                  {skill}: {score}% ({getScoreWord(score)})
                </Badge>
              ))}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Category Breakdown */}
      {categoryEntries.length > 0 && (
        <Card className="border-border/60 shadow-sm">
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-base">
              <Layers className="h-4 w-4 text-primary" />
              Category Scores
            </CardTitle>
            <CardDescription>
              Your performance across core interview areas.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
              {categoryEntries.map(([category, score]) => (
                <div key={category} className="space-y-1.5 p-3 rounded-lg bg-muted/20 border border-border/30">
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-medium text-foreground">{category}</span>
                    <span className="font-semibold text-primary font-mono">
                      {score} / 100 &bull; {getScoreWord(score)}
                    </span>
                  </div>
                  <div className="w-full bg-muted/60 h-2 rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all duration-500 ${
                        score >= 75 ? "bg-emerald-500" : score >= 50 ? "bg-amber-500" : "bg-red-500"
                      }`}
                      style={{ width: `${Math.min(100, Math.max(0, score))}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Strengths and Weaknesses Side-by-Side */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Card className="border-emerald-500/20 bg-emerald-50/10 dark:bg-emerald-950/10 shadow-sm">
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-base text-emerald-800 dark:text-emerald-400">
              <CheckCircle2 className="h-4 w-4 text-emerald-600" />
              What you did well
            </CardTitle>
          </CardHeader>
          <CardContent>
            {report.strong_areas?.length > 0 ? (
              <ul className="space-y-2 text-xs sm:text-sm text-foreground/90">
                {report.strong_areas.map((item, idx) => (
                  <li key={idx} className="flex items-start gap-2">
                    <span className="text-emerald-600 font-bold shrink-0">&bull;</span>
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-xs text-muted-foreground">No major strengths recorded.</p>
            )}
          </CardContent>
        </Card>

        <Card className="border-amber-500/20 bg-amber-50/10 dark:bg-amber-950/10 shadow-sm">
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-base text-amber-800 dark:text-amber-400">
              <TrendingUp className="h-4 w-4 text-amber-600" />
              Skills to improve
            </CardTitle>
          </CardHeader>
          <CardContent>
            {report.weak_areas?.length > 0 ? (
              <ul className="space-y-2 text-xs sm:text-sm text-foreground/90">
                {report.weak_areas.map((item, idx) => (
                  <li key={idx} className="flex items-start gap-2">
                    <span className="text-amber-600 font-bold shrink-0">&bull;</span>
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-xs text-muted-foreground">No major weaknesses identified.</p>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Resume Claims Tested (if present) */}
      {report.resume_claims_tested?.length > 0 && (
        <Card className="border-border/60 shadow-sm">
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-base">
              <FileCheck className="h-4 w-4 text-primary" />
              Resume Experience Checked
            </CardTitle>
            <CardDescription>
              Questions mapped to skills and claims on your resume.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-2.5">
              {report.resume_claims_tested.map((claim, idx) => {
                const isValidated = claim.status === "validated";
                const isWeak = claim.status === "weak";
                return (
                  <div
                    key={idx}
                    className="flex flex-col sm:flex-row sm:items-start justify-between p-3 rounded-lg border border-border/40 bg-muted/10 gap-2.5"
                  >
                    <div className="space-y-1 min-w-0 flex-1">
                      <div className="font-medium text-xs sm:text-sm text-foreground">
                        {claim.claim}
                      </div>
                      <p className="text-xs text-muted-foreground">
                        {claim.evidence}
                      </p>
                    </div>
                    <div className="shrink-0">
                      <Badge
                        variant={isValidated ? "secondary" : isWeak ? "high" : "outline"}
                        className="capitalize text-[11px]"
                      >
                        {isValidated ? "Verified" : isWeak ? "Needs detail" : claim.status}
                      </Badge>
                    </div>
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Tips / Recommendations & Practice Plan */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {report.actionable_recommendations?.length > 0 && (
          <Card className="border-border/60 shadow-sm">
            <CardHeader className="pb-3">
              <CardTitle className="flex items-center gap-2 text-base">
                <BookOpen className="h-4 w-4 text-primary" />
                Tips &amp; Recommendations
              </CardTitle>
            </CardHeader>
            <CardContent>
              <ul className="space-y-2 text-xs sm:text-sm text-muted-foreground">
                {report.actionable_recommendations.map((rec, idx) => (
                  <li key={idx} className="flex items-start gap-2">
                    <span className="font-semibold text-primary shrink-0">{idx + 1}.</span>
                    <span>{rec}</span>
                  </li>
                ))}
              </ul>
            </CardContent>
          </Card>
        )}

        {(report.ordered_practice_areas?.length ? report.ordered_practice_areas : report.ordered_next_practice_areas || []).length > 0 && (
          <Card className="border-border/60 shadow-sm">
            <CardHeader className="pb-3">
              <CardTitle className="flex items-center gap-2 text-base">
                <ListOrdered className="h-4 w-4 text-primary" />
                Next Practice Areas
              </CardTitle>
            </CardHeader>
            <CardContent>
              <ol className="space-y-2 text-xs sm:text-sm text-muted-foreground">
                {(report.ordered_practice_areas?.length ? report.ordered_practice_areas : report.ordered_next_practice_areas || []).map((area, idx) => (
                  <li key={idx} className="flex items-start gap-2">
                    <span className="rounded-full bg-primary/10 text-primary text-[10px] font-bold h-5 w-5 flex items-center justify-center shrink-0">
                      {idx + 1}
                    </span>
                    <span className="font-medium text-foreground">{area}</span>
                  </li>
                ))}
              </ol>
            </CardContent>
          </Card>
        )}
      </div>

      {/* Per-Question Feedback */}
      {answeredTurns.length > 0 && (
        <Card className="border-border/60 shadow-sm">
          <CardHeader className="pb-3">
            <CardTitle className="text-base flex items-center gap-2">
              <Sparkles className="h-4 w-4 text-primary" />
              Per-Question Feedback
            </CardTitle>
            <CardDescription>
              Detailed breakdown of each question, your answer, and feedback.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {answeredTurns.map((turn) => {
              const evalData = turn.evaluation;
              const score = evalData?.score ?? (turn.turn_score ? Math.round(turn.turn_score / 10) : null);
              return (
                <div key={turn.turn_index} className="p-4 rounded-lg border border-border/40 bg-muted/15 space-y-3">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-xs font-bold text-primary">Question {turn.turn_index + 1}</span>
                        <Badge variant="outline" className="text-[10px] capitalize">
                          {turn.category}
                        </Badge>
                        {turn.is_follow_up && (
                          <Badge variant="outline" className="text-[10px] text-amber-600 border-amber-500/30">
                            Follow-up
                          </Badge>
                        )}
                      </div>
                      <p className="font-medium text-sm text-foreground">{turn.question}</p>
                    </div>
                    {score !== null && (
                      <Badge
                        variant={score >= 7 ? "secondary" : score >= 5 ? "outline" : "high"}
                        className="font-mono text-xs shrink-0"
                      >
                        {score}/10
                      </Badge>
                    )}
                  </div>

                  <div className="p-3 bg-background rounded border border-border/30 text-xs sm:text-sm text-foreground/90 whitespace-pre-wrap">
                    <p className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wider mb-1">Your Answer</p>
                    {turn.user_answer}
                  </div>

                  {evalData?.feedback && (
                    <div className="text-xs text-muted-foreground bg-muted/40 p-2.5 rounded border border-border/30">
                      <span className="font-semibold text-foreground">Feedback: </span>
                      {evalData.feedback}
                    </div>
                  )}

                  {evalData?.strengths && evalData.strengths.length > 0 && (
                    <div className="text-xs text-emerald-800 dark:text-emerald-400 bg-emerald-50/40 dark:bg-emerald-950/20 p-2.5 rounded border border-emerald-500/20">
                      <span className="font-semibold">Strong points: </span>
                      {evalData.strengths.join(", ")}
                    </div>
                  )}
                </div>
              );
            })}
          </CardContent>
        </Card>
      )}

      {/* Bottom CTA */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-4 p-6 rounded-xl bg-card border border-border/60">
        <div>
          <div className="font-semibold text-sm text-foreground">Ready for another practice run?</div>
          <p className="text-xs text-muted-foreground">Practice another interview to keep improving.</p>
        </div>
        <div className="flex items-center gap-3">
          <Link href="/dashboard">
            <Button variant="outline" size="sm">
              Dashboard
            </Button>
          </Link>
          <Link href={`/interview/setup?role=${encodeURIComponent(report.target_role)}`}>
            <Button size="sm" className="gap-2">
              Practice Another Role
              <ArrowRight className="h-4 w-4" />
            </Button>
          </Link>
        </div>
      </div>
    </div>
  );
}
