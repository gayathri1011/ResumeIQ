"use client";

import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import {
  ArrowRight,
  BotMessageSquare,
  Briefcase,
  CheckCircle2,
  FileText,
  History,
  Layers,
  Loader2,
  Sliders,
  Sparkles,
  Target,
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
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { getUserFriendlyErrorMessage } from "@/lib/error-messages";
import { createInterviewSession } from "@/services/interview.service";
import { listResumes } from "@/services/analysis.service";
import type {
  CreateInterviewSessionRequest,
  InterviewDifficulty,
  InterviewType,
} from "@/types/interview";
import type { ResumeListItem } from "@/types/analysis";

type TargetMode = "role" | "job_desc" | "matched_job";

const DIFFICULTY_OPTIONS: { id: InterviewDifficulty; label: string; desc: string }[] = [
  { id: "junior", label: "Junior", desc: "Core concepts and fundamentals" },
  { id: "mid", label: "Mid-level", desc: "Day-to-day problem solving and best practices" },
  { id: "senior", label: "Senior", desc: "System architecture, tradeoffs, and leadership" },
  { id: "lead", label: "Lead", desc: "High-level design and technical strategy" },
];

const TYPE_OPTIONS: { id: InterviewType; label: string; desc: string }[] = [
  { id: "mixed", label: "Mixed questions", desc: "Balanced mix of technical and behavioral questions" },
  { id: "technical", label: "Technical", desc: "Coding concepts, systems, and technical problem solving" },
  { id: "behavioral", label: "Behavioral", desc: "Teamwork, handling challenges, and communication" },
  { id: "system_design", label: "System Design", desc: "Designing scalable, reliable software systems" },
];

export function InterviewSetup() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const queryRole = searchParams.get("role") || "";
  const queryJobId = searchParams.get("job_id") || "";
  const queryResumeId = searchParams.get("resume_id") || "";
  const querySkills = searchParams.get("skills") || "";

  const [mode, setMode] = useState<TargetMode>(queryJobId ? "matched_job" : "role");
  const [targetRole, setTargetRole] = useState(queryRole || "Senior Backend Engineer");
  const [jobDescriptionText, setJobDescriptionText] = useState("");
  const [jobId, setJobId] = useState(queryJobId);
  const [difficulty, setDifficulty] = useState<InterviewDifficulty>("mid");
  const [interviewType, setInterviewType] = useState<InterviewType>("mixed");
  const [questionCount, setQuestionCount] = useState<number>(5);
  const [focusSkillInput, setFocusSkillInput] = useState("");
  const [focusSkills, setFocusSkills] = useState<string[]>(
    querySkills ? querySkills.split(",").map((s) => s.trim()).filter(Boolean) : ["API Architecture", "Problem Solving"]
  );

  const [resumes, setResumes] = useState<ResumeListItem[]>([]);
  const [selectedResumeId, setSelectedResumeId] = useState<string>(queryResumeId);
  const [isLoadingResumes, setIsLoadingResumes] = useState(true);

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    async function fetchResumes() {
      try {
        const list = await listResumes();
        setResumes(list);
        const firstResume = list[0];
        if (!selectedResumeId && firstResume) {
          setSelectedResumeId(firstResume.id);
        }
      } catch (err) {
        // Non-blocking resume fetch
      } finally {
        setIsLoadingResumes(false);
      }
    }
    void fetchResumes();
  }, [selectedResumeId]);

  const handleAddSkill = () => {
    const trimmed = focusSkillInput.trim();
    if (trimmed && !focusSkills.includes(trimmed)) {
      setFocusSkills([...focusSkills, trimmed]);
      setFocusSkillInput("");
    }
  };

  const handleRemoveSkill = (skill: string) => {
    setFocusSkills(focusSkills.filter((s) => s !== skill));
  };

  const handleStart = async (e?: React.SyntheticEvent) => {
    if (e) {
      e.preventDefault();
    }
    setErrorMessage(null);

    if (!targetRole.trim()) {
      setErrorMessage("Please enter a target role or job title.");
      return;
    }

    setIsSubmitting(true);

    try {
      const payload: CreateInterviewSessionRequest = {
        target_role: targetRole.trim(),
        difficulty,
        interview_type: interviewType,
        estimated_question_count: Number(questionCount) || 5,
        focus_skills: focusSkills,
        focus_areas: focusSkills,
        resume_id: selectedResumeId ? selectedResumeId : undefined,
        job_description_id: mode === "matched_job" && jobId ? jobId : undefined,
        job_description_text: mode === "job_desc" && jobDescriptionText ? jobDescriptionText : undefined,
      };

      const session = await createInterviewSession(payload);
      router.push(`/interview/${session.id}`);
    } catch (err) {
      setErrorMessage(getUserFriendlyErrorMessage(err));
      setIsSubmitting(false);
    }
  };

  return (
    <div className="mx-auto w-full max-w-4xl space-y-8 pb-12">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-foreground sm:text-4xl">
            Practice Interview
          </h1>
          <p className="mt-1 text-muted-foreground text-sm sm:text-base">
            Practice real questions tailored to your resume and role.
          </p>
        </div>
        <Link href="/interview/history">
          <Button variant="outline" size="sm" className="gap-2">
            <History className="h-4 w-4" />
            Past Interviews
          </Button>
        </Link>
      </div>

      {errorMessage && (
        <Alert variant="error" className="flex items-center justify-between">
          <span>{errorMessage}</span>
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={handleStart}
            disabled={isSubmitting}
            className="ml-3 shrink-0 h-8"
          >
            Retry
          </Button>
        </Alert>
      )}

      <form
        onSubmit={(e) => e.preventDefault()}
        onKeyDown={(e) => {
          if (e.key === "Enter" && (e.target as HTMLElement).tagName !== "TEXTAREA") {
            e.preventDefault();
          }
        }}
        className="space-y-6"
      >
        {/* Step 1: Target Definition */}
        <Card className="border-border/60 shadow-sm">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-lg">
              <Target className="h-5 w-5 text-primary" />
              1. What role are you practicing for?
            </CardTitle>
            <CardDescription>
              Choose a role title, paste a job description, or pick a saved job.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-5">
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
              <button
                type="button"
                onClick={() => setMode("role")}
                className={`p-3 rounded-lg border text-left text-sm transition-all flex items-center gap-2.5 ${
                  mode === "role"
                    ? "border-primary bg-primary/5 text-primary font-medium ring-1 ring-primary/20"
                    : "border-border hover:bg-muted/50 text-muted-foreground"
                }`}
              >
                <Briefcase className="h-4 w-4 shrink-0" />
                <span>Role Title</span>
              </button>
              <button
                type="button"
                onClick={() => setMode("job_desc")}
                className={`p-3 rounded-lg border text-left text-sm transition-all flex items-center gap-2.5 ${
                  mode === "job_desc"
                    ? "border-primary bg-primary/5 text-primary font-medium ring-1 ring-primary/20"
                    : "border-border hover:bg-muted/50 text-muted-foreground"
                }`}
              >
                <FileText className="h-4 w-4 shrink-0" />
                <span>Job Description</span>
              </button>
              <button
                type="button"
                onClick={() => setMode("matched_job")}
                className={`p-3 rounded-lg border text-left text-sm transition-all flex items-center gap-2.5 ${
                  mode === "matched_job"
                    ? "border-primary bg-primary/5 text-primary font-medium ring-1 ring-primary/20"
                    : "border-border hover:bg-muted/50 text-muted-foreground"
                }`}
              >
                <Layers className="h-4 w-4 shrink-0" />
                <span>Saved Job</span>
              </button>
            </div>

            <div className="space-y-2">
              <Label htmlFor="targetRole">Target Role *</Label>
              <Input
                id="targetRole"
                value={targetRole}
                onChange={(e) => setTargetRole(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    e.preventDefault();
                  }
                }}
                placeholder="e.g. Junior GenAI Engineer, Staff SRE, Product Engineer"
                required
              />
            </div>

            {mode === "job_desc" && (
              <div className="space-y-2">
                <Label htmlFor="jdText">Job Description</Label>
                <textarea
                  id="jdText"
                  rows={4}
                  value={jobDescriptionText}
                  onChange={(e) => setJobDescriptionText(e.target.value)}
                  placeholder="Paste responsibilities or requirements from the job posting..."
                  className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                />
              </div>
            )}

            {mode === "matched_job" && (
              <div className="space-y-2">
                <Label htmlFor="jobId">Job Match ID</Label>
                <Input
                  id="jobId"
                  value={jobId}
                  onChange={(e) => setJobId(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") {
                      e.preventDefault();
                    }
                  }}
                  placeholder="Linked job match ID"
                />
              </div>
            )}

            {resumes.length > 0 && (
              <div className="space-y-2 pt-2 border-t border-border/40">
                <Label htmlFor="resumeSelect">Resume to practice with</Label>
                <select
                  id="resumeSelect"
                  value={selectedResumeId}
                  onChange={(e) => setSelectedResumeId(e.target.value)}
                  className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm shadow-sm"
                >
                  {resumes.map((r) => (
                    <option key={r.id} value={r.id}>
                      {r.title || r.original_filename || "Resume"} (Updated {new Date(r.updated_at).toLocaleDateString()})
                    </option>
                  ))}
                </select>
                <p className="text-xs text-muted-foreground">
                  The interviewer uses your resume to ask relevant questions about your experience.
                </p>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Step 2: Format & Difficulty */}
        <Card className="border-border/60 shadow-sm">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-lg">
              <Sliders className="h-5 w-5 text-primary" />
              2. Pick your level and question style
            </CardTitle>
            <CardDescription>
              Choose your difficulty and the kind of questions you want to practice.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="space-y-3">
              <Label>Experience level</Label>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
                {DIFFICULTY_OPTIONS.map((opt) => (
                  <button
                    key={opt.id}
                    type="button"
                    onClick={() => setDifficulty(opt.id)}
                    className={`p-3 rounded-lg border text-left transition-all ${
                      difficulty === opt.id
                        ? "border-primary bg-primary/5 text-primary ring-1 ring-primary/20"
                        : "border-border hover:bg-muted/40 text-muted-foreground"
                    }`}
                  >
                    <div className="font-semibold text-sm text-foreground">{opt.label}</div>
                    <div className="text-xs text-muted-foreground mt-0.5 leading-tight">{opt.desc}</div>
                  </button>
                ))}
              </div>
            </div>

            <div className="space-y-3">
              <Label>Question style</Label>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                {TYPE_OPTIONS.map((opt) => (
                  <button
                    key={opt.id}
                    type="button"
                    onClick={() => setInterviewType(opt.id)}
                    className={`p-3 rounded-lg border text-left transition-all ${
                      interviewType === opt.id
                        ? "border-primary bg-primary/5 text-primary ring-1 ring-primary/20"
                        : "border-border hover:bg-muted/40 text-muted-foreground"
                    }`}
                  >
                    <div className="font-semibold text-sm text-foreground">{opt.label}</div>
                    <div className="text-xs text-muted-foreground mt-0.5">{opt.desc}</div>
                  </button>
                ))}
              </div>
            </div>

            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <Label htmlFor="questionCount">Number of questions</Label>
                <span className="text-sm font-semibold text-primary">{questionCount} Questions</span>
              </div>
              <select
                id="questionCount"
                value={questionCount}
                onChange={(e) => setQuestionCount(Number(e.target.value))}
                className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
              >
                {[1, 2, 3, 4, 5, 6, 7, 8, 9, 10].map((num) => (
                  <option key={num} value={num}>
                    {num} {num === 1 ? "question" : "questions"}
                  </option>
                ))}
              </select>
              <p className="text-xs text-muted-foreground">
                Choose between 1 and 10 questions (default is 5).
              </p>
            </div>

            <div className="space-y-3">
              <Label>Skills to practice</Label>
              <div className="flex gap-2">
                <Input
                  value={focusSkillInput}
                  onChange={(e) => setFocusSkillInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") {
                      e.preventDefault();
                      handleAddSkill();
                    }
                  }}
                  placeholder="e.g. Distributed Systems, Kafka, System Design"
                  className="flex-1"
                />
                <Button type="button" variant="outline" onClick={handleAddSkill}>
                  Add Skill
                </Button>
              </div>
              <div className="flex flex-wrap gap-2 pt-1">
                {focusSkills.map((skill) => (
                  <Badge
                    key={skill}
                    variant="secondary"
                    className="gap-1.5 pl-2.5 pr-2 py-1 text-xs cursor-pointer hover:bg-destructive/10 hover:text-destructive transition-colors"
                    onClick={() => handleRemoveSkill(skill)}
                    title="Click to remove"
                  >
                    {skill}
                    <span className="text-muted-foreground hover:text-destructive">&times;</span>
                  </Badge>
                ))}
              </div>
            </div>
          </CardContent>
        </Card>

        <div className="flex flex-col sm:flex-row items-center justify-between gap-4 pt-2">
          <div className="text-xs text-muted-foreground flex items-center gap-1.5">
            <CheckCircle2 className="h-4 w-4 text-emerald-600" />
            <span>Questions adjust as you answer.</span>
          </div>
          <Button
            type="button"
            size="lg"
            onClick={handleStart}
            disabled={isSubmitting}
            className="w-full sm:w-auto min-w-[200px] gap-2 font-semibold shadow-md"
          >
            {isSubmitting ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                Setting up your interview...
              </>
            ) : (
              <>
                <BotMessageSquare className="h-4 w-4" />
                Start Interview
                <ArrowRight className="h-4 w-4" />
              </>
            )}
          </Button>
        </div>
      </form>
    </div>
  );
}
