"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { AlertCircle, Briefcase } from "lucide-react";

import { Alert } from "@/components/ui/alert";
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
import { AppShell } from "@/components/layout/AppShell";
import { PageHeader } from "@/components/layout/PageHeader";
import { JobExtractionResults } from "@/features/job/JobExtractionResults";
import { JobMatchResults } from "@/features/job/JobMatchResults";
import { JobStepIndicator } from "@/features/job/JobStepIndicator";
import { getUserFriendlyErrorMessage } from "@/lib/error-messages";
import { formControlClass, textareaClass } from "@/lib/design";
import { listResumes } from "@/services/analysis.service";
import { analyzeJobDescription } from "@/services/job.service";
import { matchJobDescription } from "@/services/match.service";
import { getJobSkillGap } from "@/services/skill-gap.service";
import type { ResumeListItem } from "@/types/analysis";
import type { JobAnalysisResult, JobAnalyzeStage } from "@/types/job";
import type { JobMatchResult, JobMatchStage } from "@/types/match";
import type { SkillGapResult } from "@/types/skill-gap";
import { SkillGapPanel } from "@/features/skill-gap/SkillGapPanel";

const MIN_WORD_COUNT = 30;

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function runAnalysisStages(
  setStage: (stage: JobAnalyzeStage) => void,
): Promise<void> {
  setStage("reading");
  await sleep(500);
  setStage("extracting");
  await sleep(600);
}

export function JobAnalyzer() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const initialResumeId = searchParams.get("resumeId");
  const versionIdParam = searchParams.get("versionId");

  const [rawText, setRawText] = useState("");
  const [company, setCompany] = useState("");
  const [selectedResumeId, setSelectedResumeId] = useState(initialResumeId ?? "");
  const [resumes, setResumes] = useState<ResumeListItem[]>([]);
  const [stage, setStage] = useState<JobAnalyzeStage>("idle");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [result, setResult] = useState<JobAnalysisResult | null>(null);
  const [matchStage, setMatchStage] = useState<JobMatchStage>("idle");
  const [matchResult, setMatchResult] = useState<JobMatchResult | null>(null);
  const [matchError, setMatchError] = useState<string | null>(null);
  const [skillGapResult, setSkillGapResult] = useState<SkillGapResult | null>(null);
  const [skillGapLoading, setSkillGapLoading] = useState(false);
  const [skillGapError, setSkillGapError] = useState<string | null>(null);

  const wordCount = useMemo(
    () => (rawText.trim() ? rawText.trim().split(/\s+/).length : 0),
    [rawText],
  );
  const charCount = rawText.length;
  const isProcessing = stage === "reading" || stage === "extracting";
  const isMatching = matchStage === "matching";
  const meetsMinWords = wordCount >= MIN_WORD_COUNT;

  useEffect(() => {
    void listResumes()
      .then(setResumes)
      .catch(() => {
        // Resume list is optional for JD analysis.
      });
  }, []);

  const reset = useCallback(() => {
    setStage("idle");
    setErrorMessage(null);
    setResult(null);
    setMatchStage("idle");
    setMatchResult(null);
    setMatchError(null);
    setSkillGapResult(null);
    setSkillGapError(null);
  }, []);

  const handleMatch = useCallback(async () => {
    if (!result || !selectedResumeId) {
      setMatchError("Select a resume before running a job match.");
      setMatchStage("error");
      return;
    }

    setMatchError(null);
    setMatchResult(null);
    setMatchStage("matching");

    try {
      const response = await matchJobDescription(result.id, {
        resume_id: selectedResumeId,
        resume_version_id: versionIdParam,
      });
      setMatchResult(response);
      setMatchStage("done");
      setSkillGapResult(null);
      setSkillGapError(null);
    } catch (error) {
      const message = getUserFriendlyErrorMessage(
        error,
        "Something went wrong while matching your resume to this job.",
      );
      setMatchError(message);
      setMatchStage("error");
    }
  }, [result, selectedResumeId, versionIdParam]);

  const handleSkillGap = useCallback(async () => {
    if (!result || !selectedResumeId) return;

    setSkillGapLoading(true);
    setSkillGapError(null);

    try {
      const response = await getJobSkillGap(
        result.id,
        selectedResumeId,
        versionIdParam,
      );
      setSkillGapResult(response);
    } catch (error) {
      const message = getUserFriendlyErrorMessage(error, "Failed to load skill gap analysis.");
      setSkillGapError(message);
    } finally {
      setSkillGapLoading(false);
    }
  }, [result, selectedResumeId, versionIdParam]);

  const handleAnalyze = useCallback(async () => {
    if (!rawText.trim()) {
      setErrorMessage("Paste a job description before analyzing.");
      setStage("error");
      return;
    }
    if (!meetsMinWords) {
      setErrorMessage(
        `This doesn't look like a full job description yet. Add at least ${MIN_WORD_COUNT} words.`,
      );
      setStage("error");
      return;
    }

    setErrorMessage(null);
    setResult(null);
    setStage("reading");

    try {
      const analysisPromise = analyzeJobDescription({
        raw_text: rawText,
        company: company.trim() || null,
        resume_id: selectedResumeId || null,
      });
      await runAnalysisStages(setStage);
      const response = await analysisPromise;
      setResult(response);
      setStage("done");
    } catch (error) {
      const message = getUserFriendlyErrorMessage(
        error,
        "Something went wrong while analyzing the job description.",
      );
      setErrorMessage(message);
      setStage("error");
    }
  }, [rawText, company, selectedResumeId, meetsMinWords]);

  return (
    <AppShell>
    <div className="mx-auto w-full max-w-4xl space-y-6">
      <PageHeader
        title="Job description analyzer"
        description="Extract structured requirements from a job posting, then match them against your resume using semantic similarity and structured analysis."
        backHref="/dashboard"
      />
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Briefcase className="h-4 w-4" />
            Job description
          </CardTitle>
          <CardDescription>
            Paste the full posting text. We&apos;ll extract skills, requirements,
            and keywords — nothing is invented beyond what&apos;s in the text.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="company">Company (optional)</Label>
              <Input
                id="company"
                placeholder="e.g. Acme Corp"
                value={company}
                onChange={(event) => setCompany(event.target.value)}
                disabled={isProcessing || isMatching}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="resume-select">Resume to match</Label>
              <select
                id="resume-select"
                className={formControlClass}
                value={selectedResumeId}
                onChange={(event) => {
                  const nextResumeId = event.target.value;
                  setSelectedResumeId(nextResumeId);
                  router.push(
                    nextResumeId
                      ? `/jobs/analyze?resumeId=${nextResumeId}`
                      : "/jobs/analyze",
                  );
                }}
                disabled={isProcessing || isMatching}
              >
                <option value="">Select a resume (optional)</option>
                {resumes.map((resume) => (
                  <option key={resume.id} value={resume.id}>
                    {resume.original_filename ?? resume.title}
                  </option>
                ))}
              </select>
              {resumes.length === 0 && (
                <p className="text-xs text-muted-foreground">
                  No resumes yet —{" "}
                  <Link href="/resumes/upload" className="underline">
                    upload one
                  </Link>{" "}
                  to link it for future matching.
                </p>
              )}
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="jd-text">Job description text</Label>
            <textarea
              id="jd-text"
              rows={14}
              className={textareaClass}
              placeholder="Paste the full job description here..."
              value={rawText}
              onChange={(event) => setRawText(event.target.value)}
              disabled={isProcessing || isMatching || stage === "done"}
            />
            <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-muted-foreground">
              <span>
                {wordCount} words · {charCount} characters
              </span>
              {!meetsMinWords && rawText.trim().length > 0 && (
                <span className="text-amber-600">
                  Minimum {MIN_WORD_COUNT} words recommended
                </span>
              )}
            </div>
          </div>

          {stage === "idle" && (
            <Button onClick={() => void handleAnalyze()} disabled={!rawText.trim()}>
              Analyze Job Description
            </Button>
          )}

          {isProcessing && (
            <div className="rounded-xl border bg-muted/30 p-6">
              <JobStepIndicator currentStage={stage} />
            </div>
          )}

          {stage === "error" && errorMessage && (
            <div className="space-y-4 rounded-xl border border-destructive/30 bg-destructive/5 p-6">
              <div className="flex items-start gap-3">
                <AlertCircle className="mt-0.5 h-5 w-5 text-destructive" />
                <div>
                  <p className="font-medium text-destructive">Analysis failed</p>
                  <p className="text-sm text-destructive/90">{errorMessage}</p>
                </div>
              </div>
              <Button onClick={reset}>Try again</Button>
            </div>
          )}

          {stage === "done" && result && (
            <div className="space-y-6">
              <JobExtractionResults result={result} />

              <Card>
                <CardHeader>
                  <CardTitle className="text-base">Job match</CardTitle>
                  <CardDescription>
                    Compare this job against your selected resume using semantic
                    embeddings and structured skill/requirement analysis.
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  {!selectedResumeId && (
                    <p className="text-sm text-muted-foreground">
                      Select a resume above to run a match.
                    </p>
                  )}

                  {selectedResumeId && matchStage === "idle" && (
                    <Button onClick={() => void handleMatch()}>
                      Run job match
                    </Button>
                  )}

                  {isMatching && (
                    <div className="rounded-xl border bg-muted/30 p-6 text-sm text-muted-foreground">
                      Computing semantic similarity and structured match breakdown…
                    </div>
                  )}

                  {matchStage === "error" && matchError && (
                    <div className="space-y-3 rounded-xl border border-destructive/30 bg-destructive/5 p-4">
                      <p className="text-sm text-destructive">{matchError}</p>
                      <Button variant="outline" size="sm" onClick={() => void handleMatch()}>
                        Retry match
                      </Button>
                    </div>
                  )}

                  {matchStage === "done" && matchResult && (
                    <>
                      <JobMatchResults result={matchResult} />
                      <div className="flex flex-wrap gap-2 pt-2">
                        <Button
                          variant="secondary"
                          onClick={() => void handleSkillGap()}
                          disabled={skillGapLoading}
                        >
                          {skillGapLoading ? "Analyzing skill gaps…" : "Analyze skill gaps"}
                        </Button>
                      </div>
                      {skillGapError && (
                        <p className="text-sm text-destructive">{skillGapError}</p>
                      )}
                      {skillGapResult && <SkillGapPanel result={skillGapResult} />}
                    </>
                  )}
                </CardContent>
              </Card>

              <div className="flex flex-wrap gap-2">
                <Button variant="outline" onClick={reset}>
                  Analyze another job
                </Button>
                {selectedResumeId && (
                  <Button variant="outline" asChild>
                    <Link href={`/dashboard?resumeId=${selectedResumeId}`}>
                      View dashboard
                    </Link>
                  </Button>
                )}
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
    </AppShell>
  );
}
