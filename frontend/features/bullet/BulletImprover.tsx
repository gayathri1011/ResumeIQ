"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import {
  AlertCircle,
  ArrowLeft,
  Check,
  Copy,
  Loader2,
  RefreshCw,
  Sparkles,
  Wand2,
} from "lucide-react";

import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { AppShell } from "@/components/layout/AppShell";
import { PageHeader } from "@/components/layout/PageHeader";
import { formControlClass } from "@/lib/design";
import { Label } from "@/components/ui/label";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { getUserFriendlyErrorMessage } from "@/lib/error-messages";
import { listResumes } from "@/services/analysis.service";
import {
  improveBullet,
  listResumeBullets,
  replaceBullet,
} from "@/services/bullet.service";
import type { ResumeListItem } from "@/types/analysis";
import type {
  BulletImproveStage,
  ImproveBulletResponse,
  ResumeBulletItem,
} from "@/types/bullet";
import { loadTargetRole } from "@/features/dashboard/utils";

export function BulletImprover() {
  const searchParams = useSearchParams();
  const initialResumeId = searchParams.get("resumeId") ?? "";
  const versionIdParam = searchParams.get("versionId");

  const [resumes, setResumes] = useState<ResumeListItem[]>([]);
  const [selectedResumeId, setSelectedResumeId] = useState(initialResumeId);
  const [bullets, setBullets] = useState<ResumeBulletItem[]>([]);
  const [selectedBullet, setSelectedBullet] = useState<ResumeBulletItem | null>(
    null,
  );
  const [stage, setStage] = useState<BulletImproveStage>("idle");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [result, setResult] = useState<ImproveBulletResponse | null>(null);
  const [copied, setCopied] = useState(false);
  const [replacePending, setReplacePending] = useState(false);

  const targetRole = useMemo(
    () => (selectedResumeId ? loadTargetRole(selectedResumeId) : ""),
    [selectedResumeId],
  );

  const isProcessing = stage === "improving";

  useEffect(() => {
    void listResumes()
      .then((items) => {
        setResumes(items);
        if (!selectedResumeId && items.length > 0 && items[0]) {
          setSelectedResumeId(items[0].id);
        }
      })
      .catch(() => {
        setErrorMessage("Could not load resumes.");
      });
  }, [selectedResumeId]);

  useEffect(() => {
    if (!selectedResumeId) {
      setBullets([]);
      return;
    }

    void listResumeBullets(selectedResumeId, versionIdParam)
      .then((items) => {
        setBullets(items);
        setSelectedBullet(null);
        setResult(null);
        setStage("idle");
        setErrorMessage(null);
      })
      .catch((error) => {
        const message = getUserFriendlyErrorMessage(
          error,
          "Could not load bullets from this resume.",
        );
        setErrorMessage(message);
        setBullets([]);
      });
  }, [selectedResumeId, versionIdParam]);

  const runImprove = useCallback(
    async (regenerate: boolean) => {
      if (!selectedBullet) return;

      setStage("improving");
      setErrorMessage(null);
      if (!regenerate) {
        setResult(null);
      }

      try {
        const response = await improveBullet({
          bullet_text: selectedBullet.text,
          resume_id: selectedResumeId || undefined,
          resume_version_id: versionIdParam,
          target_role: targetRole || undefined,
          regenerate,
          previous_improved_text: regenerate ? result?.improved_text : undefined,
        });
        setResult(response);
        setStage("done");
      } catch (error) {
        const message = getUserFriendlyErrorMessage(
          error,
          "Something went wrong while improving this bullet.",
        );
        setErrorMessage(message);
        setStage("error");
      }
    },
    [selectedBullet, selectedResumeId, versionIdParam, targetRole, result],
  );

  const handleCopy = useCallback(async () => {
    if (!result?.improved_text) return;
    try {
      await navigator.clipboard.writeText(result.improved_text);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 2000);
    } catch {
      setErrorMessage("Could not copy to clipboard.");
    }
  }, [result]);

  const handleReplace = useCallback(async () => {
    if (!result || !selectedBullet || !selectedResumeId) return;

    const confirmed = window.confirm(
      "Replace the original bullet in your saved resume with the improved version? This updates your stored resume content.",
    );
    if (!confirmed) return;

    setReplacePending(true);
    setErrorMessage(null);

    try {
      await replaceBullet({
        resume_id: selectedResumeId,
        resume_version_id: versionIdParam,
        section: selectedBullet.section,
        entry_index: selectedBullet.entry_index,
        bullet_index: selectedBullet.bullet_index,
        improved_text: result.improved_text,
      });

      const refreshed = await listResumeBullets(selectedResumeId, versionIdParam);
      setBullets(refreshed);
      const updated = refreshed.find(
        (item) =>
          item.section === selectedBullet.section &&
          item.entry_index === selectedBullet.entry_index &&
          item.bullet_index === selectedBullet.bullet_index,
      );
      if (updated) {
        setSelectedBullet(updated);
      }
    } catch (error) {
      const message = getUserFriendlyErrorMessage(error, "Could not save the improved bullet.");
      setErrorMessage(message);
    } finally {
      setReplacePending(false);
    }
  }, [result, selectedBullet, selectedResumeId, versionIdParam]);

  return (
    <AppShell>
    <div className="mx-auto max-w-4xl space-y-6">
      <PageHeader
        title="Bullet improver"
        description="Select a resume bullet to rewrite it with AI — one bullet at a time."
        backHref="/dashboard"
      />
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Choose resume</CardTitle>
          <CardDescription>
            Bullets are loaded from parsed experience and project sections.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <select
            className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm"
            value={selectedResumeId}
            onChange={(event) => setSelectedResumeId(event.target.value)}
          >
            <option value="">Select a resume…</option>
            {resumes.map((resume) => (
              <option key={resume.id} value={resume.id}>
                {resume.original_filename ?? resume.title}
              </option>
            ))}
          </select>
          {targetRole && (
            <p className="mt-2 text-xs text-muted-foreground">
              Target role from dashboard: <span className="font-medium">{targetRole}</span>
            </p>
          )}
        </CardContent>
      </Card>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Select a bullet</CardTitle>
            <CardDescription>
              Click a bullet from your experience or projects.
            </CardDescription>
          </CardHeader>
          <CardContent className="max-h-[28rem] space-y-3 overflow-y-auto">
            {bullets.length === 0 ? (
              <p className="text-sm text-muted-foreground">
                {selectedResumeId
                  ? "No bullets found in this resume."
                  : "Select a resume to see bullets."}
              </p>
            ) : (
              bullets.map((bullet) => {
                const selected =
                  selectedBullet?.section === bullet.section &&
                  selectedBullet.entry_index === bullet.entry_index &&
                  selectedBullet.bullet_index === bullet.bullet_index;

                return (
                  <button
                    key={`${bullet.section}-${bullet.entry_index}-${bullet.bullet_index}`}
                    type="button"
                    onClick={() => {
                      setSelectedBullet(bullet);
                      setResult(null);
                      setStage("idle");
                      setErrorMessage(null);
                    }}
                    className={`w-full rounded-lg border p-3 text-left text-sm transition-colors ${
                      selected
                        ? "border-primary bg-primary/5"
                        : "hover:border-muted-foreground/40"
                    }`}
                  >
                    <p className="text-xs font-medium uppercase text-muted-foreground">
                      {bullet.section} · {bullet.entry_title ?? "Untitled"}
                      {bullet.organization ? ` · ${bullet.organization}` : ""}
                    </p>
                    <p className="mt-1">{bullet.text}</p>
                  </button>
                );
              })
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Before / After</CardTitle>
            <CardDescription>
              Review the rewrite before copying or replacing.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {!selectedBullet ? (
              <p className="text-sm text-muted-foreground">
                Select a bullet to get started.
              </p>
            ) : (
              <>
                <div className="space-y-2">
                  <p className="text-xs font-medium uppercase text-muted-foreground">
                    Before
                  </p>
                  <p className="rounded-lg border bg-muted/30 p-3 text-sm">
                    {selectedBullet.text}
                  </p>
                </div>

                {result && (
                  <div className="space-y-2">
                    <p className="text-xs font-medium uppercase text-muted-foreground">
                      After
                    </p>
                    <p className="rounded-lg border border-emerald-200 bg-emerald-50/50 p-3 text-sm dark:border-emerald-900 dark:bg-emerald-950/20">
                      {result.improved_text}
                    </p>
                    <p className="text-sm text-muted-foreground">
                      {result.changes_summary}
                    </p>
                    {(result.metric_placeholder_used ||
                      result.suggested_metric_prompt) && (
                      <p className="rounded-xl border border-border/70 bg-gradient-to-b from-card to-muted/50 px-3 py-2 text-xs text-muted-foreground shadow-[inset_0_1px_0_rgba(255,255,255,0.65)]">
                        Verify factual accuracy before using this bullet. Add any
                        real metrics yourself
                        {result.suggested_metric_prompt
                          ? ` — ${result.suggested_metric_prompt}`
                          : " where placeholders appear."}
                      </p>
                    )}
                  </div>
                )}

                {errorMessage && (
                  <div className="flex items-start gap-2 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-900 dark:border-red-900 dark:bg-red-950/30 dark:text-red-200">
                    <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
                    <div className="space-y-2">
                      <p>{errorMessage}</p>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => void runImprove(Boolean(result))}
                      >
                        Retry
                      </Button>
                    </div>
                  </div>
                )}

                <div className="flex flex-wrap gap-2">
                  <Button
                    onClick={() => void runImprove(false)}
                    disabled={isProcessing}
                  >
                    {isProcessing ? (
                      <>
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        Improving…
                      </>
                    ) : (
                      <>
                        <Sparkles className="mr-2 h-4 w-4" />
                        Improve
                      </>
                    )}
                  </Button>

                  {result && (
                    <>
                      <Button
                        variant="outline"
                        onClick={() => void runImprove(true)}
                        disabled={isProcessing}
                      >
                        <RefreshCw className="mr-2 h-4 w-4" />
                        Regenerate
                      </Button>
                      <Button variant="outline" onClick={() => void handleCopy()}>
                        {copied ? (
                          <>
                            <Check className="mr-2 h-4 w-4" />
                            Copied
                          </>
                        ) : (
                          <>
                            <Copy className="mr-2 h-4 w-4" />
                            Copy
                          </>
                        )}
                      </Button>
                      <Button
                        variant="secondary"
                        onClick={() => void handleReplace()}
                        disabled={replacePending}
                      >
                        {replacePending ? (
                          <>
                            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                            Saving…
                          </>
                        ) : (
                          "Replace in resume"
                        )}
                      </Button>
                    </>
                  )}
                </div>
              </>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
    </AppShell>
  );
}
