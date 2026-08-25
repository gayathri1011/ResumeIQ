"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import {
  CheckCircle2,
  Loader2,
} from "lucide-react";

import { AppShell } from "@/components/layout/AppShell";
import { PageHeader } from "@/components/layout/PageHeader";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { FeatureSkeleton } from "@/components/ui/feature-skeleton";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { SectionComparison } from "@/features/optimization/SectionComparison";
import { loadTargetRole } from "@/features/dashboard/utils";
import { DownloadPdfButton } from "@/features/versions/DownloadPdfButton";
import { getUserFriendlyErrorMessage } from "@/lib/error-messages";
import { useActionLock } from "@/lib/use-action-lock";
import { getResume } from "@/services/analysis.service";
import {
  applyOptimization,
  getLatestOptimization,
  optimizeResume,
} from "@/services/optimize.service";
import type { ChangeDecision, OptimizationProposal } from "@/types/optimize";
import { REVIEW_SECTIONS } from "@/types/optimize";

type ReviewStatus = "loading" | "empty" | "error" | "ready" | "applying" | "applied";

export function OptimizationReview() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const resumeId = searchParams.get("resumeId") ?? "";
  const versionIdParam = searchParams.get("versionId");
  const shouldGenerate = searchParams.get("generate") === "true";

  const [status, setStatus] = useState<ReviewStatus>("loading");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [proposal, setProposal] = useState<OptimizationProposal | null>(null);
  const [targetRole, setTargetRole] = useState("");
  const [versionLabel, setVersionLabel] = useState<string | null>(null);
  const [decisions, setDecisions] = useState<Record<string, ChangeDecision>>({});
  const [applyMessage, setApplyMessage] = useState<string | null>(null);
  const runLocked = useActionLock();
  const [isGenerating, setIsGenerating] = useState(false);

  const allDecided = useMemo(() => {
    if (!proposal) return false;
    return proposal.changes.every(
      (change) => decisions[change.change_id] && decisions[change.change_id] !== "pending",
    );
  }, [proposal, decisions]);

  const loadProposal = useCallback(async () => {
    if (!resumeId) {
      setStatus("empty");
      return;
    }

    setStatus("loading");
    setErrorMessage(null);
    setApplyMessage(null);

    try {
      const role = loadTargetRole(resumeId);
      if (role) setTargetRole(role);

      const resume = await getResume(resumeId, versionIdParam);
      setVersionLabel(resume.active_version_label ?? null);

      if (shouldGenerate) {
        if (!role && !targetRole.trim()) {
          setStatus("empty");
          return;
        }
        const generated = await optimizeResume(resumeId, {
          target_role: role || targetRole,
          resume_version_id: versionIdParam,
        });
        setProposal(generated);
        setStatus("ready");
        return;
      }

      const latest = await getLatestOptimization(resumeId, versionIdParam);
      if (!latest || latest.changes.length === 0) {
        setStatus("empty");
        return;
      }
      setProposal(latest);
      setStatus("ready");
    } catch (error) {
      const message = getUserFriendlyErrorMessage(
        error,
        "Could not load the optimization proposal.",
      );
      setErrorMessage(message);
      setStatus("error");
    }
  }, [resumeId, versionIdParam, shouldGenerate, targetRole]);

  useEffect(() => {
    void loadProposal();
  }, [loadProposal]);

  useEffect(() => {
    if (!proposal) return;
    const initial: Record<string, ChangeDecision> = {};
    for (const change of proposal.changes) {
      initial[change.change_id] = "pending";
    }
    setDecisions(initial);
  }, [proposal]);

  const handleDecision = useCallback((changeId: string, decision: ChangeDecision) => {
    setDecisions((current) => ({ ...current, [changeId]: decision }));
  }, []);

  const handleBulk = useCallback(
    (action: "accept" | "reject") => {
      if (!proposal) return;
      const next: Record<string, ChangeDecision> = {};
      for (const change of proposal.changes) {
        next[change.change_id] = action;
      }
      setDecisions(next);
    },
    [proposal],
  );

  const handleApply = useCallback(async () => {
    if (!proposal || !resumeId) return;

    const acceptedCount = proposal.changes.filter(
      (change) => decisions[change.change_id] === "accept",
    ).length;

    const confirmed = window.confirm(
      acceptedCount > 0
        ? `Apply ${acceptedCount} accepted change(s) to your live resume? This updates your saved content.`
        : "No changes will be applied. Continue?",
    );
    if (!confirmed) return;

    setStatus("applying");
    setErrorMessage(null);

    try {
      const response = await applyOptimization(resumeId, {
        optimization_id: proposal.optimization_id,
        resume_version_id: versionIdParam,
        decisions: proposal.changes.map((change) => ({
          change_id: change.change_id,
          action:
            decisions[change.change_id] === "accept" ? "accept" : "reject",
        })),
      });
      setApplyMessage(response.message);
      if (response.reanalyze_recommended) {
        setApplyMessage(
          `${response.message} Your dashboard scores may be stale until you re-analyze.`,
        );
      }
      setStatus("applied");
    } catch (error) {
      const message = getUserFriendlyErrorMessage(
        error,
        "Could not apply optimization decisions.",
      );
      setErrorMessage(message);
      setStatus("ready");
    }
  }, [proposal, resumeId, versionIdParam, decisions]);

  const handleGenerate = useCallback(async () => {
    if (!resumeId || !targetRole.trim()) {
      setErrorMessage("Enter a target role to generate an optimization.");
      setStatus("empty");
      return;
    }

    await runLocked(async () => {
      setIsGenerating(true);
      setStatus("loading");
      setErrorMessage(null);
      try {
        const generated = await optimizeResume(resumeId, {
          target_role: targetRole.trim(),
          resume_version_id: versionIdParam,
        });
        setProposal(generated);
        setStatus("ready");
      } catch (error) {
        const message = getUserFriendlyErrorMessage(
          error,
          "Optimization failed. Please try again.",
        );
        setErrorMessage(message);
        setStatus("error");
      } finally {
        setIsGenerating(false);
      }
    });
  }, [resumeId, versionIdParam, targetRole, runLocked]);

  if (!resumeId) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Select a resume</CardTitle>
          <CardDescription>
            Open this page from your dashboard or add `?resumeId=...` to the URL.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Button asChild>
            <Link href="/dashboard">Go to dashboard</Link>
          </Button>
        </CardContent>
      </Card>
    );
  }

  return (
    <AppShell>
    <div className="space-y-6">
      <PageHeader
        title="Optimization review"
        description="Compare the original resume with the AI proposal, then accept or reject each change."
        backHref={`/dashboard?resumeId=${resumeId}${versionIdParam ? `&versionId=${versionIdParam}` : ""}`}
        actions={
          versionIdParam ? (
            <DownloadPdfButton
              resumeId={resumeId}
              versionId={versionIdParam}
              versionLabel={versionLabel}
            />
          ) : null
        }
      />

      {status === "loading" ? <FeatureSkeleton cardHeight="h-72" /> : null}

      {status === "empty" && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">No optimization to review yet</CardTitle>
            <CardDescription>
              Generate a role-targeted optimization proposal first.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <label className="text-sm font-medium" htmlFor="target-role">
                Target role
              </label>
              <Input
                id="target-role"
                value={targetRole}
                onChange={(event) => setTargetRole(event.target.value)}
                placeholder="e.g. Senior Backend Engineer"
              />
            </div>
            <Button
              onClick={() => void handleGenerate()}
              disabled={!targetRole.trim() || isGenerating}
            >
              {isGenerating ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Generating…
                </>
              ) : (
                "Generate optimization"
              )}
            </Button>
          </CardContent>
        </Card>
      )}

      {status === "error" && errorMessage ? (
        <Alert variant="error" title="Could not load optimization">
          <div className="space-y-3">
            <p>{errorMessage}</p>
            <Button variant="outline" size="sm" onClick={() => void loadProposal()}>
              Retry
            </Button>
          </div>
        </Alert>
      ) : null}

      {(status === "ready" || status === "applying" || status === "applied") && proposal && (
        <>
          <Card>
            <CardHeader>
              <CardTitle className="text-base">
                Proposal for {proposal.target_role}
              </CardTitle>
              <CardDescription>
                {proposal.optimization_mode === "jd_grounded"
                  ? "Grounded in a linked job description and skill-gap context."
                  : "Target-role optimization without a linked job description."}
              </CardDescription>
            </CardHeader>
            <CardContent className="flex flex-wrap gap-2">
              <Button variant="outline" size="sm" onClick={() => handleBulk("accept")}>
                Accept all
              </Button>
              <Button variant="outline" size="sm" onClick={() => handleBulk("reject")}>
                Reject all
              </Button>
              <Button
                size="sm"
                onClick={() => void handleApply()}
                disabled={status === "applying" || !allDecided}
              >
                {status === "applying" ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Applying…
                  </>
                ) : (
                  "Apply decisions"
                )}
              </Button>
            </CardContent>
          </Card>

          {!allDecided ? (
            <p className="text-sm text-muted-foreground">
              Accept or reject each proposed change before applying.
            </p>
          ) : null}

          {applyMessage ? (
            <Alert variant="success" title="Optimization applied">
              <div className="space-y-2">
                <p>{applyMessage}</p>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() =>
                    router.push(
                      `/dashboard?resumeId=${resumeId}${versionIdParam ? `&versionId=${versionIdParam}` : ""}`,
                    )
                  }
                >
                  Back to dashboard
                </Button>
              </div>
            </Alert>
          ) : null}

          <div className="space-y-6">
            {REVIEW_SECTIONS.map((section) => (
              <SectionComparison
                key={section.key}
                sectionKey={section.key}
                label={section.label}
                beforeValue={proposal.original_content[section.key]}
                afterValue={proposal.optimized_content[section.key]}
                changes={proposal.changes}
                decisions={decisions}
                onDecision={handleDecision}
              />
            ))}
          </div>
        </>
      )}
    </div>
    </AppShell>
  );
}
