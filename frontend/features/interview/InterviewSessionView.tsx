"use client";

import { useEffect, useState, useRef } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import {
  AlertCircle,
  ArrowRight,
  BotMessageSquare,
  CheckCircle,
  ChevronDown,
  ChevronUp,
  Clock,
  HelpCircle,
  Loader2,
  Send,
  Sparkles,
  StopCircle,
  Zap,
} from "lucide-react";

import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { getUserFriendlyErrorMessage } from "@/lib/error-messages";
import {
  endInterviewSession,
  getInterviewSession,
  submitTurnAnswer,
} from "@/services/interview.service";
import type {
  InterviewSession,
  InterviewTurn,
  TurnEvaluation,
} from "@/types/interview";

interface InterviewSessionViewProps {
  sessionId: string;
}

export function InterviewSessionView({ sessionId }: InterviewSessionViewProps) {
  const router = useRouter();

  const [session, setSession] = useState<InterviewSession | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  const [currentAnswer, setCurrentAnswer] = useState("");
  const [isSubmittingAnswer, setIsSubmittingAnswer] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const [isEndingSession, setIsEndingSession] = useState(false);
  const [showEndDialog, setShowEndDialog] = useState(false);

  const [expandedTurns, setExpandedTurns] = useState<Record<number, boolean>>({});

  const answerTextareaRef = useRef<HTMLTextAreaElement>(null);

  const fetchSession = async () => {
    try {
      setLoadError(null);
      const data = await getInterviewSession(sessionId);
      setSession(data);
      if (data.status === "completed") {
        router.push(`/interview/${sessionId}/report`);
      }
    } catch (err) {
      setLoadError(getUserFriendlyErrorMessage(err, "Something went wrong. Please try again."));
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    void fetchSession();
  }, [sessionId]);

  const activeTurn: InterviewTurn | null =
    session && session.status !== "completed" && session.current_turn_index < session.turns.length
      ? (session.turns[session.current_turn_index] ?? null)
      : null;

  const toggleTurnExpand = (idx: number) => {
    setExpandedTurns((prev) => ({
      ...prev,
      [idx]: !prev[idx],
    }));
  };

  const handleSubmitAnswer = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!session || !activeTurn || isSubmittingAnswer) return;

    const trimmed = currentAnswer.trim();
    if (!trimmed) {
      setSubmitError("Please write an answer before submitting.");
      return;
    }

    setIsSubmittingAnswer(true);
    setSubmitError(null);

    try {
      const evaluation: TurnEvaluation = await submitTurnAnswer(
        sessionId,
        activeTurn.turn_index,
        trimmed,
      );

      setCurrentAnswer("");

      if (evaluation.is_complete) {
        router.push(`/interview/${sessionId}/report`);
      } else {
        await fetchSession();
        setTimeout(() => {
          answerTextareaRef.current?.focus();
        }, 100);
      }
    } catch (err) {
      setSubmitError(getUserFriendlyErrorMessage(err, "Something went wrong. Please try again."));
    } finally {
      setIsSubmittingAnswer(false);
    }
  };

  const handleEndEarly = async () => {
    setIsEndingSession(true);
    setShowEndDialog(false);
    try {
      await endInterviewSession(sessionId);
      router.push(`/interview/${sessionId}/report`);
    } catch (err) {
      setSubmitError(getUserFriendlyErrorMessage(err, "Something went wrong. Please try again."));
      setIsEndingSession(false);
    }
  };

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[50vh] space-y-4">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
        <p className="text-sm text-muted-foreground">Setting up your interview questions...</p>
      </div>
    );
  }

  if (loadError || !session) {
    return (
      <div className="mx-auto max-w-lg py-12 space-y-4">
        <Alert variant="error">
          <AlertCircle className="h-4 w-4" />
          <span>{loadError || "Something went wrong. Please try again."}</span>
        </Alert>
        <div className="flex justify-center gap-3">
          <Button variant="outline" onClick={() => void fetchSession()}>
            Retry
          </Button>
          <Link href="/interview/setup">
            <Button>Start New Interview</Button>
          </Link>
        </div>
      </div>
    );
  }

  const completedTurns = session.turns.filter((t) => t.user_answer !== null);
  const plannedCount = session.plan?.estimated_question_count || 5;
  const currentTurnDisplay = Math.min(session.current_turn_index + 1, plannedCount);
  const progressPercent = Math.min(100, Math.round((completedTurns.length / plannedCount) * 100));

  return (
    <div className="mx-auto w-full max-w-4xl space-y-6 pb-16">
      {/* Header bar */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-border/50 pb-4">
        <div>
          <div className="flex items-center gap-2">
            <Badge variant="secondary" className="capitalize">
              {session.difficulty} Level
            </Badge>
            <Badge variant="outline" className="capitalize">
              {session.interview_type}
            </Badge>
          </div>
          <h1 className="text-2xl font-bold tracking-tight mt-1 text-foreground">
            {session.target_role}
          </h1>
        </div>

        <div className="flex items-center gap-3">
          <div className="text-right text-xs text-muted-foreground hidden sm:block">
            <div>Question {currentTurnDisplay} of {plannedCount}</div>
            <div className="font-semibold text-foreground">{completedTurns.length} Answered</div>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setShowEndDialog(true)}
            disabled={isEndingSession || isSubmittingAnswer}
            className="text-muted-foreground hover:text-destructive hover:border-destructive/40 gap-1.5"
          >
            <StopCircle className="h-4 w-4" />
            End Interview
          </Button>
        </div>
      </div>

      {/* Progress tracker */}
      <div className="w-full bg-muted/60 h-2 rounded-full overflow-hidden">
        <div
          className="bg-primary h-full transition-all duration-500 rounded-full"
          style={{ width: `${progressPercent}%` }}
        />
      </div>

      {/* End Session Confirmation Dialog */}
      <Dialog open={showEndDialog} onOpenChange={setShowEndDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Finish interview now?</DialogTitle>
            <DialogDescription>
              Your feedback will be based on the{" "}
              {completedTurns.length} question(s) answered so far.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter className="gap-2 sm:gap-0">
            <Button variant="ghost" onClick={() => setShowEndDialog(false)}>
              Keep Practicing
            </Button>
            <Button
              variant="destructive"
              onClick={handleEndEarly}
              disabled={isEndingSession}
              className="gap-2"
            >
              {isEndingSession ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
              Finish &amp; View Feedback
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Active Question Card */}
      {activeTurn ? (
        <Card className="border-primary/20 shadow-md bg-card/80 backdrop-blur-sm ring-1 ring-primary/10">
          <CardHeader className="space-y-2 pb-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="flex h-7 w-7 items-center justify-center rounded-full bg-primary/10 text-primary font-bold text-xs">
                  Q{activeTurn.turn_index + 1}
                </span>
                <Badge variant="secondary" className="capitalize text-xs font-normal">
                  {activeTurn.category}
                </Badge>
                {activeTurn.is_follow_up && (
                  <Badge variant="outline" className="text-amber-600 dark:text-amber-400 border-amber-500/30 text-xs">
                    Follow-up question
                  </Badge>
                )}
              </div>
              <div className="text-xs text-muted-foreground">
                Question {activeTurn.turn_index + 1} of {plannedCount}
              </div>
            </div>
            <CardTitle className="text-lg sm:text-xl font-semibold leading-relaxed pt-1 text-foreground">
              {activeTurn.question}
            </CardTitle>
            {activeTurn.skill_tags.length > 0 && (
              <div className="flex flex-wrap gap-1.5 pt-1">
                {activeTurn.skill_tags.map((tag) => (
                  <Badge key={tag} variant="outline" className="text-[11px] py-0 px-2 text-muted-foreground">
                    {tag}
                  </Badge>
                ))}
              </div>
            )}
          </CardHeader>

          <form onSubmit={handleSubmitAnswer}>
            <CardContent className="space-y-3 pt-2">
              {submitError && (
                <Alert variant="error" className="py-2 text-xs flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <AlertCircle className="h-3.5 w-3.5 shrink-0" />
                    <span>{submitError}</span>
                  </div>
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    className="h-7 text-xs px-2"
                    onClick={() => void handleSubmitAnswer()}
                    disabled={isSubmittingAnswer}
                  >
                    Retry
                  </Button>
                </Alert>
              )}

              <div className="space-y-1.5">
                <textarea
                  ref={answerTextareaRef}
                  value={currentAnswer}
                  onChange={(e) => setCurrentAnswer(e.target.value)}
                  disabled={isSubmittingAnswer}
                  rows={6}
                  placeholder="Type your answer here. Explain your approach, key decisions, and real-world experience..."
                  className="w-full rounded-md border border-input bg-background/90 px-3.5 py-3 text-sm shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40 disabled:opacity-50 resize-y"
                  onKeyDown={(e) => {
                    if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
                      e.preventDefault();
                      void handleSubmitAnswer();
                    }
                  }}
                />
                <div className="flex items-center justify-between text-xs text-muted-foreground px-1">
                  <span>Press <kbd className="rounded bg-muted px-1.5 py-0.5 text-[10px] font-mono border">Ctrl+Enter</kbd> to submit</span>
                  <span>{currentAnswer.length} characters</span>
                </div>
              </div>
            </CardContent>

            <CardFooter className="flex items-center justify-between border-t border-border/40 pt-4 pb-4">
              <div className="text-xs text-muted-foreground flex items-center gap-1.5">
                <Zap className="h-3.5 w-3.5 text-amber-500" />
                <span>Checks your technical answers and communication</span>
              </div>

              <Button
                type="submit"
                disabled={isSubmittingAnswer || !currentAnswer.trim()}
                className="gap-2 shadow-sm font-medium"
              >
                {isSubmittingAnswer ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Checking your answer...
                  </>
                ) : (
                  <>
                    <span>Submit Answer</span>
                    <Send className="h-4 w-4" />
                  </>
                )}
              </Button>
            </CardFooter>
          </form>
        </Card>
      ) : null}

      {/* Conversation & Evaluation History */}
      {completedTurns.length > 0 && (
        <div className="space-y-4 pt-4">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-semibold text-foreground flex items-center gap-2">
              <CheckCircle className="h-4 w-4 text-emerald-600" />
              Questions answered ({completedTurns.length})
            </h2>
          </div>

          <div className="space-y-3">
            {completedTurns.map((turn) => {
              const isExpanded = expandedTurns[turn.turn_index] ?? true;
              const evalData = turn.evaluation;
              const score = evalData?.score ?? (turn.turn_score ? Math.round(turn.turn_score / 10) : null);

              return (
                <Card key={turn.turn_index} className="border-border/60 bg-card/60 overflow-hidden">
                  <div
                    onClick={() => toggleTurnExpand(turn.turn_index)}
                    className="flex items-center justify-between p-4 cursor-pointer hover:bg-muted/30 transition-colors"
                  >
                    <div className="flex items-center gap-3 min-w-0 pr-2">
                      <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-muted text-muted-foreground font-semibold text-xs">
                        Q{turn.turn_index + 1}
                      </span>
                      <div className="truncate font-medium text-sm text-foreground">
                        {turn.question}
                      </div>
                    </div>
                    <div className="flex items-center gap-3 shrink-0">
                      {score !== null && (
                        <Badge
                          variant={score >= 7 ? "secondary" : score >= 5 ? "outline" : "high"}
                          className="font-mono text-xs"
                        >
                          {score}/10
                        </Badge>
                      )}
                      {isExpanded ? (
                        <ChevronUp className="h-4 w-4 text-muted-foreground" />
                      ) : (
                        <ChevronDown className="h-4 w-4 text-muted-foreground" />
                      )}
                    </div>
                  </div>

                  {isExpanded && (
                    <CardContent className="border-t border-border/40 space-y-4 pt-4 bg-muted/10 text-sm">
                      <div>
                        <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-1">
                          Your Answer
                        </div>
                        <p className="text-foreground/90 whitespace-pre-wrap bg-background/80 p-3 rounded-md border border-border/40 text-xs sm:text-sm">
                          {turn.user_answer}
                        </p>
                      </div>

                      {evalData && (
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-1">
                          {evalData.strengths?.length > 0 && (
                            <div className="space-y-1 bg-emerald-50/50 dark:bg-emerald-950/20 p-3 rounded-md border border-emerald-500/20">
                              <div className="text-xs font-semibold text-emerald-800 dark:text-emerald-400">
                                What you did well
                              </div>
                              <ul className="text-xs space-y-1 text-emerald-900 dark:text-emerald-300 list-disc list-inside">
                                {evalData.strengths.map((str, sIdx) => (
                                  <li key={sIdx}>{str}</li>
                                ))}
                              </ul>
                            </div>
                          )}

                          {evalData.missing_points?.length > 0 && (
                            <div className="space-y-1 bg-amber-50/50 dark:bg-amber-950/20 p-3 rounded-md border border-amber-500/20">
                              <div className="text-xs font-semibold text-amber-800 dark:text-amber-400">
                                Things to improve
                              </div>
                              <ul className="text-xs space-y-1 text-amber-900 dark:text-amber-300 list-disc list-inside">
                                {evalData.missing_points.map((miss, mIdx) => (
                                  <li key={mIdx}>{miss}</li>
                                ))}
                              </ul>
                            </div>
                          )}

                          {evalData.feedback && (
                            <div className="md:col-span-2 text-xs text-muted-foreground bg-muted/40 p-2.5 rounded border border-border/30">
                              <span className="font-semibold text-foreground">Feedback: </span>
                              {evalData.feedback}
                            </div>
                          )}
                        </div>
                      )}
                    </CardContent>
                  )}
                </Card>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
