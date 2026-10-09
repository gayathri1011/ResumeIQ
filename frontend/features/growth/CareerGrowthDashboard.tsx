"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import {
  AlertCircle,
  ArrowRight,
  BotMessageSquare,
  Briefcase,
  Check,
  CheckCircle2,
  Clock,
  Compass,
  Copy,
  ExternalLink,
  History,
  Layers,
  ListFilter,
  Loader2,
  RefreshCw,
  Rocket,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
  Target,
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
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { CircularScore } from "@/features/dashboard/CircularScore";
import { getUserFriendlyErrorMessage } from "@/lib/error-messages";
import { listResumes } from "@/services/analysis.service";
import {
  createGrowthPlan,
  getLatestGrowthPlan,
  refreshGrowthPlan,
  updateMilestoneStatus,
} from "@/services/growth.service";
import type { ResumeListItem } from "@/types/analysis";
import type {
  CareerGrowthPlan,
  EvidenceClass,
  MilestoneStatus,
  ProjectRecommendation,
  RoadmapMilestone,
  SkillGap,
} from "@/types/growth";

const OTHER_ROLE_VALUE = "__other__";

const COMMON_ROLES = [
  "Senior Backend Engineer",
  "GenAI Engineer",
  "ML Engineer",
  "Data Scientist",
  "Cloud Engineer",
  "Software Engineer",
  "Full Stack Engineer",
  "DevOps / Platform Engineer",
];

const EVIDENCE_CLASS_CONFIG: Record<
  EvidenceClass,
  { label: string; variant: "success" | "secondary" | "outline" | "high" }
> = {
  "evidence-backed": { label: "Shown in your resume", variant: "success" },
  inferred: { label: "Likely from your background", variant: "secondary" },
  unverified: { label: "Needs practice", variant: "outline" },
  missing: { label: "Skill to learn", variant: "high" },
};

function getScoreWord(score: number): string {
  if (score >= 75) return "Strong";
  if (score >= 55) return "Getting there";
  return "Needs work";
}

export function CareerGrowthDashboard() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const queryRole = searchParams.get("role") || "";
  const queryResumeId = searchParams.get("resume_id") || "";

  const [resumes, setResumes] = useState<ResumeListItem[]>([]);
  const [selectedResumeId, setSelectedResumeId] = useState<string>(queryResumeId);
  const [selectedRoleOption, setSelectedRoleOption] = useState<string>(
    queryRole && !COMMON_ROLES.includes(queryRole)
      ? OTHER_ROLE_VALUE
      : (queryRole || "Senior Backend Engineer"),
  );
  const [customRoleInput, setCustomRoleInput] = useState<string>(
    queryRole && !COMMON_ROLES.includes(queryRole) ? queryRole : "",
  );

  const [plan, setPlan] = useState<CareerGrowthPlan | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false);
  const [isGenerating, setIsGenerating] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<
    "roadmap" | "gaps" | "projects" | "evidence"
  >("roadmap");

  const [copiedProjectId, setCopiedProjectId] = useState<string | null>(null);
  const [updatingMilestoneId, setUpdatingMilestoneId] = useState<string | null>(
    null,
  );

  const loadInitialData = async () => {
    setIsLoading(true);
    setErrorMessage(null);
    try {
      const resumeList = await listResumes();
      setResumes(resumeList);
      if (!selectedResumeId && resumeList[0]) {
        setSelectedResumeId(resumeList[0].id);
      }

      // Fetch latest plan for role or general
      try {
        const existingPlan = await getLatestGrowthPlan(queryRole || undefined);
        if (existingPlan) {
          setPlan(existingPlan);
          if (COMMON_ROLES.includes(existingPlan.target_role)) {
            setSelectedRoleOption(existingPlan.target_role);
            setCustomRoleInput("");
          } else {
            setSelectedRoleOption(OTHER_ROLE_VALUE);
            setCustomRoleInput(existingPlan.target_role);
          }
        } else {
          setPlan(null);
        }
      } catch {
        // No active plan yet; friendly empty state
        setPlan(null);
      }
    } catch (err) {
      setErrorMessage(
        getUserFriendlyErrorMessage(
          err,
          "Could not load your career data. Please try again.",
        ),
      );
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    void loadInitialData();
  }, [queryRole]);

  const handleGeneratePlan = async (roleToUse?: string) => {
    const rawRole =
      roleToUse ||
      (selectedRoleOption === OTHER_ROLE_VALUE
        ? customRoleInput
        : selectedRoleOption);
    const chosenRole = rawRole.trim();
    if (!chosenRole) {
      setErrorMessage("Please enter a target role.");
      return;
    }

    setIsGenerating(true);
    setErrorMessage(null);
    try {
      const newPlan = await createGrowthPlan({
        resume_id: selectedResumeId || null,
        target_role: chosenRole,
      });
      setPlan(newPlan);
      if (COMMON_ROLES.includes(newPlan.target_role)) {
        setSelectedRoleOption(newPlan.target_role);
        setCustomRoleInput("");
      } else {
        setSelectedRoleOption(OTHER_ROLE_VALUE);
        setCustomRoleInput(newPlan.target_role);
      }
    } catch (err) {
      setErrorMessage(
        getUserFriendlyErrorMessage(
          err,
          "Failed to build career growth plan. Please try again.",
        ),
      );
    } finally {
      setIsGenerating(false);
    }
  };

  const handleRefreshPlan = async () => {
    if (!plan) return;
    setIsRefreshing(true);
    setErrorMessage(null);
    try {
      const refreshed = await refreshGrowthPlan(plan.id);
      setPlan(refreshed);
    } catch (err) {
      setErrorMessage(
        getUserFriendlyErrorMessage(
          err,
          "Failed to refresh plan with latest assessments.",
        ),
      );
    } finally {
      setIsRefreshing(false);
    }
  };

  const handleToggleMilestone = async (
    milestone: RoadmapMilestone,
    newStatus: MilestoneStatus,
  ) => {
    if (!plan) return;
    setUpdatingMilestoneId(milestone.milestone_id);
    try {
      const updatedPlan = await updateMilestoneStatus(
        plan.id,
        milestone.milestone_id,
        {
          status: newStatus,
          evidence_type: "self_reported",
        },
      );
      setPlan(updatedPlan);
    } catch (err) {
      setErrorMessage(
        getUserFriendlyErrorMessage(
          err,
          "Could not update milestone status.",
        ),
      );
    } finally {
      setUpdatingMilestoneId(null);
    }
  };

  const copyResumeBullet = (text: string, projectId: string) => {
    navigator.clipboard.writeText(text);
    setCopiedProjectId(projectId);
    setTimeout(() => setCopiedProjectId(null), 2500);
  };

  return (
    <div className="mx-auto max-w-6xl space-y-8 pb-16">
      {/* Header */}
      <div className="flex flex-col justify-between gap-4 md:flex-row md:items-center">
        <div>
          <h1 className="font-display text-3xl font-medium tracking-tight text-foreground sm:text-4xl">
            Career Growth
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Skills you need for your next role, with practice interviews.
          </p>
        </div>

        {plan && (
          <div className="flex items-center gap-3">
            <Button
              variant="outline"
              size="sm"
              onClick={handleRefreshPlan}
              disabled={isRefreshing}
              className="gap-2"
            >
              <RefreshCw
                className={`h-4 w-4 ${isRefreshing ? "animate-spin" : ""}`}
              />
              Refresh
            </Button>
            <Link
              href={`/interview?role=${encodeURIComponent(
                plan.target_role,
              )}&resume_id=${selectedResumeId || ""}`}
            >
              <Button size="sm" className="gap-2">
                <BotMessageSquare className="h-4 w-4" />
                Practice Interview
              </Button>
            </Link>
          </div>
        )}
      </div>

      {errorMessage && (
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-4 rounded-lg border border-destructive/30 bg-destructive/5 text-destructive">
          <div className="flex items-center gap-2 text-sm">
            <AlertCircle className="h-4 w-4 shrink-0" />
            <span>{errorMessage}</span>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={() => void loadInitialData()}
            className="shrink-0 gap-1.5 self-start sm:self-auto border-destructive/30 hover:bg-destructive/10"
          >
            <RefreshCw className="h-3.5 w-3.5" />
            Retry
          </Button>
        </div>
      )}

      {/* Target Role & Controls Bar */}
      <Card className="border-border/70 shadow-sm">
        <CardContent className="p-4 sm:p-6">
          <div className="grid gap-4 md:grid-cols-12 md:items-end">
            <div className="space-y-1.5 md:col-span-5">
              <Label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                Target Role
              </Label>
              <select
                value={selectedRoleOption}
                onChange={(e) => {
                  const val = e.target.value;
                  setSelectedRoleOption(val);
                  if (val !== OTHER_ROLE_VALUE && plan && plan.target_role !== val) {
                    void handleGeneratePlan(val);
                  }
                }}
                className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm shadow-sm focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
              >
                {COMMON_ROLES.map((role) => (
                  <option key={role} value={role}>
                    {role}
                  </option>
                ))}
                <option value={OTHER_ROLE_VALUE}>Other / type your own role</option>
              </select>

              {selectedRoleOption === OTHER_ROLE_VALUE && (
                <div className="pt-2">
                  <Input
                    value={customRoleInput}
                    onChange={(e) => setCustomRoleInput(e.target.value)}
                    placeholder="e.g. iOS Engineer, Security Architect"
                    maxLength={100}
                    className="w-full text-sm"
                    required
                  />
                </div>
              )}
            </div>

            <div className="space-y-1.5 md:col-span-4">
              <Label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                Resume to use
              </Label>
              <select
                value={selectedResumeId}
                onChange={(e) => setSelectedResumeId(e.target.value)}
                className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm shadow-sm focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
              >
                {resumes.map((r) => (
                  <option key={r.id} value={r.id}>
                    {r.title || "Untitled Resume"}
                  </option>
                ))}
              </select>
            </div>

            <div className="md:col-span-3">
              <Button
                onClick={() => void handleGeneratePlan()}
                disabled={isGenerating || isLoading}
                className="w-full gap-2"
              >
                {isGenerating ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Creating your plan...
                  </>
                ) : (
                  <>
                    <Target className="h-4 w-4" />
                    {plan ? "Update my plan" : "Create my plan"}
                  </>
                )}
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Main Content Area */}
      {isLoading ? (
        <div className="flex flex-col items-center justify-center py-20 text-muted-foreground">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
          <p className="mt-3 text-sm">Loading your growth plan...</p>
        </div>
      ) : !plan ? (
        <Card className="border-dashed py-16 text-center">
          <CardContent className="space-y-4">
            <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-primary/10 text-primary">
              <Target className="h-7 w-7" />
            </div>
            <div className="mx-auto max-w-md space-y-1">
              <h3 className="font-display text-xl font-medium">
                You don&apos;t have a growth plan yet
              </h3>
              <p className="text-sm text-muted-foreground">
                Pick your target role to see the skills you need and a step-by-step plan.
              </p>
            </div>
            <Button
              onClick={() => void handleGeneratePlan()}
              disabled={isGenerating}
              className="gap-2"
            >
              {isGenerating ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Sparkles className="h-4 w-4" />
              )}
              Create my plan
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-8">
          {/* Progress Overview Card */}
          <Card className="border-border/70 shadow-sm">
            <CardHeader className="pb-4">
              <CardTitle className="font-display text-xl">
                Your progress
              </CardTitle>
              <CardDescription>
                {plan.readiness_score}% match for {plan.target_role}
              </CardDescription>
            </CardHeader>

            <CardContent className="space-y-6">
              <div className="grid gap-6 md:grid-cols-12 md:items-center">
                <div className="flex flex-col items-center justify-center border-b border-border/60 pb-6 md:col-span-4 md:border-b-0 md:border-r md:pb-0 md:pr-6">
                  <CircularScore
                    score={plan.readiness_score}
                    size={130}
                    strokeWidth={10}
                    label="Role match"
                  />
                  <div className="mt-3 text-center">
                    <Badge variant="outline" className="text-xs">
                      {getScoreWord(plan.readiness_score)}
                    </Badge>
                  </div>
                </div>

                <div className="space-y-4 md:col-span-8">
                  <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                    <div className="rounded-lg border border-border/60 bg-muted/20 p-3">
                      <p className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                        Skills to improve
                      </p>
                      <p className="mt-1 text-xl font-bold tabular-nums text-destructive">
                        {
                          plan.skill_gaps.filter(
                            (g) => g.priority === "high" && g.status !== "verified",
                          ).length
                        }
                      </p>
                    </div>

                    <div className="rounded-lg border border-border/60 bg-muted/20 p-3">
                      <p className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                        Skills shown
                      </p>
                      <p className="mt-1 text-xl font-bold tabular-nums text-success">
                        {
                          plan.skill_gaps.filter(
                            (g) => g.status === "verified",
                          ).length
                        }
                      </p>
                    </div>

                    <div className="rounded-lg border border-border/60 bg-muted/20 p-3">
                      <p className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                        Steps completed
                      </p>
                      <p className="mt-1 text-xl font-bold tabular-nums">
                        {plan.roadmap_phases.reduce(
                          (acc, p) =>
                            acc +
                            p.milestones.filter((m) => m.status === "completed")
                              .length,
                          0,
                        )}
                        /
                        {plan.roadmap_phases.reduce(
                          (acc, p) => acc + p.milestones.length,
                          0,
                        )}
                      </p>
                    </div>

                    <div className="rounded-lg border border-border/60 bg-muted/20 p-3">
                      <p className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                        Projects
                      </p>
                      <p className="mt-1 text-xl font-bold tabular-nums text-primary">
                        {plan.project_recommendations.length}
                      </p>
                    </div>
                  </div>

                  {plan.summary && (
                    <p className="text-xs leading-relaxed text-muted-foreground">
                      {plan.summary}
                    </p>
                  )}
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Navigation Tabs */}
          <div className="flex border-b border-border/70 overflow-x-auto">
            <button
              type="button"
              onClick={() => setActiveTab("roadmap")}
              className={`flex items-center gap-2 border-b-2 px-5 py-3 text-sm font-medium transition shrink-0 ${
                activeTab === "roadmap"
                  ? "border-primary text-primary"
                  : "border-transparent text-muted-foreground hover:text-foreground"
              }`}
            >
              <Layers className="h-4 w-4" />
              Your Plan ({plan.roadmap_phases.length} Phases)
            </button>

            <button
              type="button"
              onClick={() => setActiveTab("gaps")}
              className={`flex items-center gap-2 border-b-2 px-5 py-3 text-sm font-medium transition shrink-0 ${
                activeTab === "gaps"
                  ? "border-primary text-primary"
                  : "border-transparent text-muted-foreground hover:text-foreground"
              }`}
            >
              <Target className="h-4 w-4" />
              Skills to improve ({plan.skill_gaps.length})
            </button>

            <button
              type="button"
              onClick={() => setActiveTab("projects")}
              className={`flex items-center gap-2 border-b-2 px-5 py-3 text-sm font-medium transition shrink-0 ${
                activeTab === "projects"
                  ? "border-primary text-primary"
                  : "border-transparent text-muted-foreground hover:text-foreground"
              }`}
            >
              <Rocket className="h-4 w-4" />
              Projects ({plan.project_recommendations.length})
            </button>

            <button
              type="button"
              onClick={() => setActiveTab("evidence")}
              className={`flex items-center gap-2 border-b-2 px-5 py-3 text-sm font-medium transition shrink-0 ${
                activeTab === "evidence"
                  ? "border-primary text-primary"
                  : "border-transparent text-muted-foreground hover:text-foreground"
              }`}
            >
              <History className="h-4 w-4" />
              Activity &amp; Proof ({plan.change_logs.length})
            </button>
          </div>

          {/* TAB 1: PHASED ROADMAP */}
          {activeTab === "roadmap" && (
            <div className="space-y-6">
              {plan.roadmap_phases.map((phase) => (
                <Card key={phase.phase_number} className="border-border/70 shadow-sm">
                  <CardHeader className="bg-muted/10 pb-3">
                    <div className="flex flex-col justify-between gap-2 sm:flex-row sm:items-center">
                      <div>
                        <div className="flex items-center gap-2">
                          <Badge variant="outline" className="text-xs font-semibold">
                            Phase {phase.phase_number}
                          </Badge>
                          <span className="text-xs text-muted-foreground">
                            Approx. {phase.duration_weeks} weeks
                          </span>
                        </div>
                        <CardTitle className="mt-1 font-display text-lg">
                          {phase.name}
                        </CardTitle>
                      </div>

                      {phase.focus_skills.length > 0 && (
                        <div className="flex flex-wrap gap-1.5">
                          {phase.focus_skills.map((s) => (
                            <Badge key={s} variant="secondary" className="text-[11px]">
                              {s}
                            </Badge>
                          ))}
                        </div>
                      )}
                    </div>
                  </CardHeader>

                  <CardContent className="divide-y divide-border/60 p-0">
                    {phase.milestones.map((m) => (
                      <div
                        key={m.milestone_id}
                        className="flex flex-col justify-between gap-4 p-4 transition hover:bg-muted/5 sm:flex-row sm:items-center sm:p-5"
                      >
                        <div className="space-y-1.5">
                          <div className="flex flex-wrap items-center gap-2">
                            <span className="font-medium text-foreground">
                              {m.title}
                            </span>
                            <Badge
                              variant={
                                m.priority === "high"
                                  ? "high"
                                  : m.priority === "medium"
                                    ? "medium"
                                    : "low"
                              }
                              className="text-[10px]"
                            >
                              {m.priority.toUpperCase()} PRIORITY
                            </Badge>
                            <span className="text-xs text-muted-foreground">
                              Effort: {m.estimated_effort}
                            </span>
                          </div>

                          <p className="text-xs text-muted-foreground">
                            {m.why_it_matters}
                          </p>

                          {m.practical_exercise && (
                            <p className="text-xs text-primary/90">
                              <strong>Exercise:</strong> {m.practical_exercise}
                            </p>
                          )}

                          {m.prerequisites.length > 0 && (
                            <div className="flex items-center gap-1.5 text-[11px] text-muted-foreground">
                              <span>Prerequisites:</span>
                              {m.prerequisites.map((p) => (
                                <span
                                  key={p}
                                  className="rounded bg-muted px-1.5 py-0.5 text-[10px]"
                                >
                                  {p}
                                </span>
                              ))}
                            </div>
                          )}
                        </div>

                        {/* Status Toggle Controls */}
                        <div className="flex shrink-0 items-center gap-2">
                          {m.skill && (
                            <Link
                              href={`/interview?role=${encodeURIComponent(
                                plan.target_role,
                              )}&skills=${encodeURIComponent(
                                m.skill,
                              )}&resume_id=${selectedResumeId || ""}`}
                            >
                              <Button
                                size="sm"
                                variant="outline"
                                className="h-8 gap-1.5 text-xs"
                              >
                                <BotMessageSquare className="h-3.5 w-3.5 text-primary" />
                                Practice
                              </Button>
                            </Link>
                          )}

                          <select
                            value={m.status}
                            disabled={updatingMilestoneId === m.milestone_id}
                            onChange={(e) =>
                              handleToggleMilestone(
                                m,
                                e.target.value as MilestoneStatus,
                              )
                            }
                            className={`h-8 rounded-md border px-2.5 text-xs font-medium shadow-sm focus:outline-none ${
                              m.status === "completed"
                                ? "border-success/30 bg-success/10 text-success"
                                : m.status === "in_progress"
                                  ? "border-primary/30 bg-primary/10 text-primary"
                                  : "border-input bg-background text-muted-foreground"
                            }`}
                          >
                            <option value="not_started">Not Started</option>
                            <option value="in_progress">In Progress</option>
                            <option value="completed">Completed</option>
                          </select>
                        </div>
                      </div>
                    ))}
                  </CardContent>
                </Card>
              ))}
            </div>
          )}

          {/* TAB 2: SKILL GAPS */}
          {activeTab === "gaps" && (
            <div className="grid gap-4 md:grid-cols-2">
              {plan.skill_gaps.map((gap) => {
                const conf =
                  EVIDENCE_CLASS_CONFIG[gap.evidence_class as EvidenceClass] ||
                  EVIDENCE_CLASS_CONFIG["missing"];

                return (
                  <Card
                    key={gap.skill}
                    className="flex flex-col justify-between border-border/70 shadow-sm"
                  >
                    <CardHeader className="pb-3">
                      <div className="flex items-start justify-between gap-2">
                        <div>
                          <CardTitle className="font-display text-lg">
                            {gap.skill}
                          </CardTitle>
                          <div className="mt-1 flex flex-wrap items-center gap-2">
                            <Badge variant={conf.variant} className="text-[10px]">
                              {conf.label}
                            </Badge>
                            <Badge
                              variant={
                                gap.priority === "high"
                                  ? "high"
                                  : gap.priority === "medium"
                                    ? "medium"
                                    : "low"
                              }
                              className="text-[10px]"
                            >
                              {gap.priority.toUpperCase()} PRIORITY
                            </Badge>
                            <span className="text-xs text-muted-foreground">
                              {gap.importance} for role
                            </span>
                          </div>
                        </div>

                        {gap.status === "verified" ? (
                          <div className="flex items-center gap-1 rounded-full bg-success/10 px-2 py-0.5 text-xs font-semibold text-success">
                            <ShieldCheck className="h-3.5 w-3.5" />
                            Verified
                          </div>
                        ) : (
                          <div className="flex items-center gap-1 rounded-full bg-destructive/10 px-2 py-0.5 text-xs font-semibold text-destructive">
                            <AlertCircle className="h-3.5 w-3.5" />
                            Needs practice
                          </div>
                        )}
                      </div>
                    </CardHeader>

                    <CardContent className="space-y-3">
                      <div className="grid grid-cols-2 gap-2 rounded-lg bg-muted/20 p-2 text-xs">
                        <div>
                          <span className="text-[10px] uppercase text-muted-foreground">
                            Current level:
                          </span>
                          <p className="font-semibold capitalize">
                            {gap.current_level}
                          </p>
                        </div>
                        <div>
                          <span className="text-[10px] uppercase text-muted-foreground">
                            Goal level:
                          </span>
                          <p className="font-semibold capitalize text-primary">
                            {gap.required_level}
                          </p>
                        </div>
                      </div>

                      <p className="text-xs text-muted-foreground">
                        {gap.why_it_matters}
                      </p>

                      {gap.evidence.length > 0 && gap.evidence[0] && (
                        <div className="space-y-1 rounded border border-border/50 bg-background/50 p-2 text-xs">
                          <span className="text-[10px] font-semibold uppercase text-muted-foreground">
                            Found in your resume:
                          </span>
                          <p className="italic text-foreground/85">
                            &ldquo;{gap.evidence[0]}&rdquo;
                          </p>
                        </div>
                      )}

                      <div className="pt-2">
                        <Link
                          href={`/interview?role=${encodeURIComponent(
                            plan.target_role,
                          )}&skills=${encodeURIComponent(
                            gap.skill,
                          )}&resume_id=${selectedResumeId || ""}`}
                          className="w-full"
                        >
                          <Button
                            variant="outline"
                            size="sm"
                            className="w-full gap-2 border-primary/30 text-xs text-primary hover:bg-primary/5"
                          >
                            <BotMessageSquare className="h-3.5 w-3.5" />
                            Practice in an interview
                            <ArrowRight className="h-3 w-3" />
                          </Button>
                        </Link>
                      </div>
                    </CardContent>
                  </Card>
                );
              })}
            </div>
          )}

          {/* TAB 3: RECOMMENDED PROJECTS */}
          {activeTab === "projects" && (
            <div className="grid gap-6 md:grid-cols-2">
              {plan.project_recommendations.map((proj) => (
                <Card
                  key={proj.project_id}
                  className="flex flex-col justify-between border-border/70 shadow-sm"
                >
                  <CardHeader className="pb-3">
                    <div className="flex items-start justify-between gap-2">
                      <div>
                        <div className="flex items-center gap-2">
                          <Badge variant="secondary" className="text-[10px]">
                            {proj.difficulty.toUpperCase()}
                          </Badge>
                          <span className="text-xs text-muted-foreground">
                            Addresses {proj.gaps_addressed.length} Gaps
                          </span>
                        </div>
                        <CardTitle className="mt-1 font-display text-lg">
                          {proj.title}
                        </CardTitle>
                      </div>
                      <Rocket className="h-5 w-5 text-primary" />
                    </div>
                  </CardHeader>

                  <CardContent className="space-y-4">
                    <p className="text-xs leading-relaxed text-muted-foreground">
                      {proj.why_this_project || proj.description}
                    </p>

                    {proj.architecture_overview && (
                      <div className="rounded-lg border border-border/60 bg-muted/20 p-3 text-xs">
                        <p className="font-semibold uppercase tracking-wider text-muted-foreground text-[10px]">
                          Architecture Overview:
                        </p>
                        <p className="mt-1 font-mono text-[11px] text-foreground">
                          {proj.architecture_overview}
                        </p>
                      </div>
                    )}

                    <div className="space-y-1.5">
                      <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                        Technologies:
                      </p>
                      <div className="flex flex-wrap gap-1">
                        {proj.suggested_technologies.map((t) => (
                          <Badge
                            key={t}
                            variant="outline"
                            className="bg-background text-[10px]"
                          >
                            {t}
                          </Badge>
                        ))}
                      </div>
                    </div>

                    {proj.key_deliverables.length > 0 && (
                      <div className="space-y-1">
                        <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                          Key Deliverables:
                        </p>
                        <ul className="space-y-1 text-xs text-muted-foreground">
                          {proj.key_deliverables.map((d) => (
                            <li key={d} className="flex items-start gap-1.5">
                              <CheckCircle2 className="mt-0.5 h-3.5 w-3.5 shrink-0 text-success" />
                              <span>{d}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {/* Resume Bullet Point Preview */}
                    {(proj.resume_evidence || proj.resume_bullet_preview) && (
                      <div className="rounded-lg border border-success/30 bg-success/5 p-3 text-xs">
                        <div className="flex items-center justify-between">
                          <p className="font-semibold text-success text-[10px] uppercase">
                            Bullet point for your resume:
                          </p>
                          <button
                            type="button"
                            onClick={() =>
                              copyResumeBullet(
                                proj.resume_evidence ||
                                  proj.resume_bullet_preview,
                                proj.project_id,
                              )
                            }
                            className="inline-flex items-center gap-1 text-[10px] text-muted-foreground hover:text-foreground"
                          >
                            {copiedProjectId === proj.project_id ? (
                              <>
                                <Check className="h-3 w-3 text-success" />
                                Copied!
                              </>
                            ) : (
                              <>
                                <Copy className="h-3 w-3" />
                                Copy
                              </>
                            )}
                          </button>
                        </div>
                        <p className="mt-1 italic text-foreground/90 leading-relaxed">
                          &ldquo;
                          {proj.resume_evidence || proj.resume_bullet_preview}
                          &rdquo;
                        </p>
                      </div>
                    )}
                  </CardContent>
                </Card>
              ))}
            </div>
          )}

          {/* TAB 4: WHAT CHANGED & EVIDENCE LOG */}
          {activeTab === "evidence" && (
            <div className="space-y-6">
              {/* What Changed Feed */}
              <Card className="border-border/70 shadow-sm">
                <CardHeader>
                  <CardTitle className="font-display text-lg flex items-center gap-2">
                    <History className="h-5 w-5 text-primary" />
                    Recent Activity
                  </CardTitle>
                  <CardDescription>
                    How your score and skills have updated over time.
                  </CardDescription>
                </CardHeader>

                <CardContent className="divide-y divide-border/60 p-0">
                  {plan.change_logs.length === 0 ? (
                    <p className="p-6 text-sm text-muted-foreground">
                      No changes recorded yet. Complete an interview or step to
                      see updates here.
                    </p>
                  ) : (
                    plan.change_logs
                      .slice()
                      .reverse()
                      .map((log) => (
                        <div
                          key={log.change_id}
                          className="flex items-start gap-3 p-4 sm:p-5"
                        >
                          <div className="mt-1 rounded-full bg-primary/10 p-1.5 text-primary">
                            <Sparkles className="h-4 w-4" />
                          </div>
                          <div className="space-y-1">
                            <div className="flex items-center gap-2">
                              <span className="text-xs font-semibold capitalize text-foreground">
                                {log.change_type.replace("_", " ")}
                              </span>
                              <span className="text-[11px] text-muted-foreground">
                                {new Date(log.timestamp).toLocaleString()}
                              </span>
                            </div>
                            <p className="text-xs leading-relaxed text-foreground/90">
                              {log.message}
                            </p>
                            {log.affected_skills.length > 0 && (
                              <div className="flex flex-wrap gap-1 pt-1">
                                {log.affected_skills.map((s) => (
                                  <Badge
                                    key={s}
                                    variant="outline"
                                    className="text-[10px]"
                                  >
                                    {s}
                                  </Badge>
                                ))}
                              </div>
                            )}
                          </div>
                        </div>
                      ))
                  )}
                </CardContent>
              </Card>

              {/* Ingested Evidence Events Table */}
              <Card className="border-border/70 shadow-sm">
                <CardHeader>
                  <CardTitle className="font-display text-lg flex items-center gap-2">
                    <ShieldCheck className="h-5 w-5 text-success" />
                    Verified Proof ({plan.evidence_events.length})
                  </CardTitle>
                  <CardDescription>
                    Proof from your interviews, projects, and completed steps.
                  </CardDescription>
                </CardHeader>

                <CardContent>
                  {plan.evidence_events.length === 0 ? (
                    <p className="py-4 text-sm text-muted-foreground">
                      No verified proof yet. Complete an interview practice session to earn proof.
                    </p>
                  ) : (
                    <div className="overflow-x-auto">
                      <table className="w-full text-left text-xs">
                        <thead>
                          <tr className="border-b border-border/70 text-muted-foreground">
                            <th className="pb-2 font-medium">Skill</th>
                            <th className="pb-2 font-medium">Source Type</th>
                            <th className="pb-2 font-medium">Score</th>
                            <th className="pb-2 font-medium">Credibility Weight</th>
                            <th className="pb-2 font-medium">Recorded</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-border/60">
                          {plan.evidence_events.map((ev) => (
                            <tr key={ev.event_id}>
                              <td className="py-2.5 font-semibold text-foreground">
                                {ev.skill}
                              </td>
                              <td className="py-2.5">
                                <Badge
                                  variant={
                                    ev.source_type === "interview"
                                      ? "success"
                                      : "outline"
                                  }
                                  className="text-[10px]"
                                >
                                  {ev.source_type}
                                </Badge>
                              </td>
                              <td className="py-2.5 tabular-nums">
                                {ev.score}%
                              </td>
                              <td className="py-2.5 tabular-nums text-muted-foreground">
                                {ev.weight.toFixed(2)}x
                              </td>
                              <td className="py-2.5 text-muted-foreground">
                                {new Date(ev.recorded_at).toLocaleDateString()}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </CardContent>
              </Card>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
