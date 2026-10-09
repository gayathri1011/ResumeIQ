"use client";

import { useEffect, useState, useRef } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import {
  AlertCircle,
  Loader2,
  Mic,
  Send,
  Square,
  StopCircle,
} from "lucide-react";

import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
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

  // Web Speech API state
  const [isListening, setIsListening] = useState(false);
  const [speechSupported, setSpeechSupported] = useState(false);
  const [speechError, setSpeechError] = useState<string | null>(null);

  const answerTextareaRef = useRef<HTMLTextAreaElement>(null);
  const recognitionRef = useRef<any>(null);
  const shouldListenRef = useRef(false);
  const baseTextRef = useRef<string>("");

  useEffect(() => {
    if (typeof window !== "undefined") {
      const hasSpeech = Boolean(
        (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition,
      );
      setSpeechSupported(hasSpeech);
    }

    return () => {
      shouldListenRef.current = false;
      if (recognitionRef.current) {
        try {
          recognitionRef.current.abort();
        } catch {
          // ignore
        }
      }
    };
  }, []);

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

  const stopListening = () => {
    shouldListenRef.current = false;
    setIsListening(false);
    if (recognitionRef.current) {
      try {
        recognitionRef.current.stop();
      } catch {
        // ignore
      }
    }
  };

  const startListening = () => {
    if (typeof window === "undefined") return;
    const SpeechRecognition =
      (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;

    if (!SpeechRecognition) {
      setSpeechError("Voice input works in Chrome and Edge.");
      return;
    }

    setSpeechError(null);
    baseTextRef.current = currentAnswer;
    shouldListenRef.current = true;

    try {
      if (recognitionRef.current) {
        try {
          recognitionRef.current.abort();
        } catch {
          // ignore
        }
      }

      const recognition = new SpeechRecognition();
      recognition.continuous = true;
      recognition.interimResults = true;
      recognition.lang =
        typeof navigator !== "undefined" && navigator.language ? navigator.language : "en-US";

      recognition.onstart = () => {
        setIsListening(true);
        setSpeechError(null);
      };

      recognition.onresult = (event: any) => {
        let finalTranscript = "";
        let interimTranscript = "";

        for (let i = 0; i < event.results.length; i++) {
          const item = event.results[i];
          if (item.isFinal) {
            finalTranscript += item[0].transcript;
          } else {
            interimTranscript += item[0].transcript;
          }
        }

        const base = baseTextRef.current.trim();
        const finalClean = finalTranscript.trim();
        const interimClean = interimTranscript.trim();

        const parts = [base, finalClean, interimClean].filter(Boolean);
        setCurrentAnswer(parts.join(" "));
      };

      recognition.onerror = (event: any) => {
        if (event.error === "not-allowed" || event.error === "service-not-allowed") {
          shouldListenRef.current = false;
          setIsListening(false);
          setSpeechError("Microphone access is blocked. Allow it in your browser settings.");
        } else if (event.error === "no-speech") {
          // Quietly ignore; onend will restart if continuous mode stopped
        } else {
          // Other errors: stop quietly
          shouldListenRef.current = false;
          setIsListening(false);
        }
      };

      recognition.onend = () => {
        if (shouldListenRef.current) {
          setCurrentAnswer((prev) => {
            baseTextRef.current = prev;
            return prev;
          });
          try {
            recognition.start();
            return;
          } catch {
            shouldListenRef.current = false;
            setIsListening(false);
          }
        } else {
          setIsListening(false);
        }
      };

      recognitionRef.current = recognition;
      recognition.start();
    } catch {
      shouldListenRef.current = false;
      setIsListening(false);
      setSpeechError("Could not start microphone.");
    }
  };

  const toggleListening = () => {
    if (isListening) {
      stopListening();
    } else {
      startListening();
    }
  };

  const handleSubmitAnswer = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!session || !activeTurn || isSubmittingAnswer) return;

    stopListening();

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
      baseTextRef.current = "";

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
    stopListening();

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
  const plannedCount =
    session.estimated_question_count || session.plan?.estimated_question_count || session.turns.length || 5;
  const currentTurnDisplay = Math.min(plannedCount, Math.max(1, completedTurns.length + 1));
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
            <Button
              variant="outline"
              onClick={() => setShowEndDialog(false)}
              disabled={isEndingSession}
            >
              Continue Practice
            </Button>
            <Button
              variant="default"
              onClick={() => void handleEndEarly()}
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
                  Q{currentTurnDisplay}
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
              <div className="text-xs text-muted-foreground font-medium">
                Question {currentTurnDisplay} of {plannedCount}
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
                <div className="relative rounded-md border border-input bg-background/90 shadow-sm transition-colors focus-within:ring-2 focus-within:ring-primary/40 focus-within:border-primary/50">
                  <textarea
                    ref={answerTextareaRef}
                    value={currentAnswer}
                    onChange={(e) => {
                      setCurrentAnswer(e.target.value);
                      baseTextRef.current = e.target.value;
                    }}
                    disabled={isSubmittingAnswer}
                    rows={6}
                    placeholder="Type your answer here, or click the mic to speak..."
                    className="w-full bg-transparent px-3.5 pt-3 pb-12 text-sm focus:outline-none disabled:opacity-50 resize-y rounded-md border-0"
                    onKeyDown={(e) => {
                      if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
                        e.preventDefault();
                        void handleSubmitAnswer();
                      }
                    }}
                  />

                  {/* Inside bottom controls: Listening status on left, mic button on right */}
                  <div className="pointer-events-none absolute bottom-2.5 left-3 right-3 flex items-center justify-between">
                    <div className="pointer-events-auto">
                      {isListening && (
                        <span className="flex items-center gap-1.5 text-xs text-primary font-medium animate-pulse">
                          <span className="h-1.5 w-1.5 rounded-full bg-primary animate-ping" />
                          Listening...
                        </span>
                      )}
                    </div>

                    <div className="pointer-events-auto">
                      {speechSupported ? (
                        <button
                          type="button"
                          onClick={toggleListening}
                          disabled={isSubmittingAnswer}
                          aria-label={isListening ? "Stop voice input" : "Start voice input"}
                          title={isListening ? "Stop voice input" : "Start voice input"}
                          className={`flex h-9 w-9 items-center justify-center rounded-full transition-all duration-200 ${
                            isListening
                              ? "bg-primary text-primary-foreground shadow-sm ring-4 ring-primary/20 animate-pulse"
                              : "text-muted-foreground hover:text-foreground hover:bg-muted/80 bg-background border border-border/60 shadow-xs"
                          }`}
                        >
                          {isListening ? (
                            <Square className="h-3.5 w-3.5 fill-current" />
                          ) : (
                            <Mic className="h-4 w-4" />
                          )}
                        </button>
                      ) : (
                        <button
                          type="button"
                          disabled
                          aria-label="Voice input not supported"
                          title="Voice input works in Chrome and Edge"
                          className="flex h-9 w-9 items-center justify-center rounded-full text-muted-foreground/40 cursor-not-allowed bg-muted/40 border border-border/30"
                        >
                          <Mic className="h-4 w-4 opacity-40" />
                        </button>
                      )}
                    </div>
                  </div>
                </div>

                {speechError && (
                  <p className="text-xs text-amber-600 dark:text-amber-400 px-1 pt-1">{speechError}</p>
                )}
              </div>
            </CardContent>

            <CardFooter className="flex items-center justify-end border-t border-border/40 pt-4 pb-4">
              <Button
                type="submit"
                disabled={isSubmittingAnswer || !currentAnswer.trim()}
                className="gap-2 shadow-sm font-medium"
              >
                {isSubmittingAnswer ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Saving your answer...
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
    </div>
  );
}
