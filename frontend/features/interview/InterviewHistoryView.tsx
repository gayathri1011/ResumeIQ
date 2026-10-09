"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  AlertCircle,
  ArrowRight,
  BotMessageSquare,
  Calendar,
  CheckCircle,
  Clock,
  History,
  Layers,
  Loader2,
  Plus,
  Sparkles,
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
import { listInterviewSessions } from "@/services/interview.service";
import type { InterviewSessionListItem } from "@/types/interview";

export function InterviewHistoryView() {
  const [sessions, setSessions] = useState<InterviewSessionListItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const fetchHistory = async () => {
    try {
      setIsLoading(true);
      setErrorMessage(null);
      const data = await listInterviewSessions(30, 0);
      setSessions(data);
    } catch (err) {
      setErrorMessage(getUserFriendlyErrorMessage(err, "Something went wrong. Please try again."));
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    void fetchHistory();
  }, []);

  return (
    <div className="mx-auto w-full max-w-4xl space-y-6 pb-16">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-border/50 pb-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-foreground mt-1">
            Past Interviews
          </h1>
          <p className="text-xs sm:text-sm text-muted-foreground mt-1">
            Review your past interview practice and feedback.
          </p>
        </div>

        <Link href="/interview/setup">
          <Button size="sm" className="gap-2 shadow-sm">
            <Plus className="h-4 w-4" />
            Start Interview
          </Button>
        </Link>
      </div>

      {errorMessage && (
        <Alert variant="error" className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <AlertCircle className="h-4 w-4 shrink-0" />
            <span>{errorMessage}</span>
          </div>
          <Button variant="outline" size="sm" onClick={() => void fetchHistory()}>
            Retry
          </Button>
        </Alert>
      )}

      {isLoading ? (
        <div className="flex flex-col items-center justify-center min-h-[35vh] space-y-3">
          <Loader2 className="h-7 w-7 animate-spin text-primary" />
          <p className="text-sm text-muted-foreground">Loading past interviews...</p>
        </div>
      ) : sessions.length === 0 ? (
        <Card className="border-dashed border-border/80 text-center p-8 sm:p-12">
          <CardContent className="space-y-4">
            <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-primary/10 text-primary">
              <BotMessageSquare className="h-7 w-7" />
            </div>
            <div className="space-y-1">
              <h2 className="text-lg font-semibold text-foreground">No interviews yet. Start your first one.</h2>
              <p className="text-sm text-muted-foreground max-w-md mx-auto">
                Practice answering interview questions tailored to your resume.
              </p>
            </div>
            <Link href="/interview/setup">
              <Button className="gap-2">
                Start your first interview
                <ArrowRight className="h-4 w-4" />
              </Button>
            </Link>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-3">
          {sessions.map((sess) => {
            const isCompleted = sess.status === "completed";
            const dateStr = new Date(sess.completed_at || sess.created_at).toLocaleDateString(undefined, {
              month: "short",
              day: "numeric",
              year: "numeric",
            });

            return (
              <Card
                key={sess.id}
                className="border-border/60 hover:border-primary/40 transition-colors shadow-sm bg-card/70"
              >
                <CardContent className="p-4 sm:p-5 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
                  <div className="space-y-1.5 min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <h2 className="font-semibold text-base text-foreground truncate">
                        {sess.target_role}
                      </h2>
                      <Badge variant="outline" className="capitalize text-[11px]">
                        {sess.difficulty}
                      </Badge>
                      <Badge
                        variant={isCompleted ? "secondary" : "outline"}
                        className="text-[11px] capitalize"
                      >
                        {sess.status === "completed" ? "Completed" : "In progress"}
                      </Badge>
                    </div>

                    <div className="flex items-center gap-4 text-xs text-muted-foreground">
                      <span className="flex items-center gap-1">
                        <Calendar className="h-3.5 w-3.5" />
                        {dateStr}
                      </span>
                      <span>{sess.turns_count ?? sess.total_turns ?? 0} Questions</span>
                      {sess.readiness_status && (
                        <span className="capitalize font-medium text-foreground">
                          {sess.readiness_status.replace("_", " ")}
                        </span>
                      )}
                    </div>

                    {(sess.top_strengths?.length ? sess.top_strengths : sess.main_strengths ?? []).length > 0 && (
                      <div className="text-xs text-muted-foreground truncate pt-0.5">
                        <span className="font-medium text-foreground">Strengths: </span>
                        {(sess.top_strengths?.length ? sess.top_strengths : sess.main_strengths ?? []).join(", ")}
                      </div>
                    )}
                  </div>

                  <div className="flex items-center gap-4 w-full sm:w-auto justify-between sm:justify-end border-t sm:border-t-0 pt-3 sm:pt-0 border-border/40">
                    {sess.overall_score !== null ? (
                      <div className="text-right">
                        <div className="text-xl font-bold font-mono text-primary">
                          {sess.overall_score}
                          <span className="text-xs font-normal text-muted-foreground">/100</span>
                        </div>
                        <div className="text-[10px] text-muted-foreground">
                          {sess.overall_score >= 75 ? "Strong" : sess.overall_score >= 50 ? "Getting there" : "Needs work"}
                        </div>
                      </div>
                    ) : (
                      <div className="text-xs text-muted-foreground">In progress</div>
                    )}

                    {isCompleted ? (
                      <Link href={`/interview/${sess.id}/report`}>
                        <Button variant="outline" size="sm" className="gap-1.5">
                          View feedback
                          <ArrowRight className="h-3.5 w-3.5" />
                        </Button>
                      </Link>
                    ) : (
                      <Link href={`/interview/${sess.id}`}>
                        <Button size="sm" className="gap-1.5">
                          Continue
                          <ArrowRight className="h-3.5 w-3.5" />
                        </Button>
                      </Link>
                    )}
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}
