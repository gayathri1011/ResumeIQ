import type { AnalysisIssue, ResumeAnalysis } from "@/types/analysis";

const ISSUE_CATEGORY_MAP: Record<string, string[]> = {
  overall: [],
  ats: ["ats", "ats_compatibility", "formatting_issues", "keywords"],
  skills: ["skills"],
  content_quality: [
    "content_quality",
    "readability",
    "relevance",
    "professional_summary",
    "action_verbs",
    "quantifiable_achievements",
    "achievements",
  ],
  projects: ["projects"],
  experience: ["experience"],
};

export function getGreeting(): string {
  return "Welcome";
}

export function getCategoryScore(
  analysis: ResumeAnalysis,
  categoryKey: string,
): number | null {
  const scores = analysis.category_scores;
  if (categoryKey in scores && typeof scores[categoryKey] === "number") {
    return scores[categoryKey];
  }
  return null;
}

export function getDimensionExplanation(
  analysis: ResumeAnalysis,
  dimensionKey: string | null,
): string | null {
  if (!dimensionKey) return null;
  const dimension = analysis.dimensions.find((d) => d.key === dimensionKey);
  return dimension?.explanation ?? null;
}

export function getIssuesForScope(
  issues: AnalysisIssue[],
  scopeKey: string,
): AnalysisIssue[] {
  if (scopeKey === "overall") return issues;
  const allowed = ISSUE_CATEGORY_MAP[scopeKey] ?? [scopeKey];
  return issues.filter((issue) =>
    allowed.includes(issue.category.toLowerCase()),
  );
}

import { scoreStrokeHex, scoreTextClass } from "@/lib/design";

export function scoreColor(score: number): string {
  return scoreTextClass(score);
}

export function scoreStrokeColor(score: number): string {
  return scoreStrokeHex(score);
}

export function fixActionLabel(category: string): string {
  const key = category.toLowerCase();
  if (key.includes("experience") || key.includes("project")) {
    return "Open bullet improver";
  }
  if (key.includes("skill")) {
    return "Review skills on dashboard";
  }
  if (key.includes("ats") || key.includes("format")) {
    return "Review ATS tips on dashboard";
  }
  return "Open bullet improver";
}

const TARGET_ROLE_STORAGE_KEY = "resumeiq-target-role";

export function loadTargetRole(resumeId: string): string {
  if (typeof window === "undefined") return "";
  try {
    const raw = localStorage.getItem(TARGET_ROLE_STORAGE_KEY);
    if (!raw) return "";
    const map = JSON.parse(raw) as Record<string, string>;
    return map[resumeId] ?? "";
  } catch {
    return "";
  }
}

export function saveTargetRole(resumeId: string, role: string): void {
  if (typeof window === "undefined") return;
  try {
    const raw = localStorage.getItem(TARGET_ROLE_STORAGE_KEY);
    const map = raw ? (JSON.parse(raw) as Record<string, string>) : {};
    map[resumeId] = role;
    localStorage.setItem(TARGET_ROLE_STORAGE_KEY, JSON.stringify(map));
  } catch {
    // ignore storage errors
  }
}
