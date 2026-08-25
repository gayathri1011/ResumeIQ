"use client";

import { useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ChangeWhyNote } from "@/features/optimization/ChangeWhyNote";
import {
  buildSkillReorderMeta,
  detectAddedKeywords,
  getChangesForSection,
  isSkillsReorderChange,
  renderKeywordHighlights,
} from "@/features/optimization/diffUtils";
import type { ChangeDecision, OptimizationChange } from "@/types/optimize";

interface SectionComparisonProps {
  sectionKey: string;
  label: string;
  beforeValue: unknown;
  afterValue: unknown;
  changes: OptimizationChange[];
  decisions: Record<string, ChangeDecision>;
  onDecision: (changeId: string, decision: ChangeDecision) => void;
}

function formatSectionValue(value: unknown): string {
  if (value == null) return "";
  if (Array.isArray(value)) {
    if (value.every((item) => typeof item === "string")) {
      return value.join(", ");
    }
    return JSON.stringify(value, null, 2);
  }
  if (typeof value === "object") {
    return JSON.stringify(value, null, 2);
  }
  return String(value);
}

function renderExperienceProjects(value: unknown) {
  if (!Array.isArray(value)) {
    return <p className="whitespace-pre-wrap text-sm">{formatSectionValue(value)}</p>;
  }

  return (
    <div className="space-y-3">
      {value.map((entry, index) => {
        if (!entry || typeof entry !== "object") return null;
        const item = entry as Record<string, unknown>;
        return (
          <div key={`${String(item.title)}-${index}`} className="rounded-md border p-3">
            <p className="text-sm font-medium">{String(item.title ?? "Untitled")}</p>
            {item.organization ? (
              <p className="text-xs text-muted-foreground">{String(item.organization)}</p>
            ) : null}
            {item.date_range ? (
              <p className="text-xs text-muted-foreground">{String(item.date_range)}</p>
            ) : null}
            {item.description ? (
              <p className="mt-2 whitespace-pre-wrap text-sm">{String(item.description)}</p>
            ) : null}
          </div>
        );
      })}
    </div>
  );
}

export function SectionComparison({
  sectionKey,
  label,
  beforeValue,
  afterValue,
  changes,
  decisions,
  onDecision,
}: SectionComparisonProps) {
  const [mobileView, setMobileView] = useState<"before" | "after">("before");
  const sectionChanges = getChangesForSection(changes, sectionKey);
  const hasChanges = sectionChanges.length > 0;

  if (!hasChanges) {
    return (
      <section className="rounded-lg border border-dashed p-4">
        <h3 className="text-sm font-medium">{label}</h3>
        <p className="mt-2 text-sm text-muted-foreground">
          No meaningful changes proposed for this section.
        </p>
        {beforeValue != null && beforeValue !== "" ? (
          <div className="mt-3 text-sm text-muted-foreground">
            {sectionKey === "experience" || sectionKey === "projects"
              ? renderExperienceProjects(beforeValue)
              : formatSectionValue(beforeValue)}
          </div>
        ) : null}
      </section>
    );
  }

  return (
    <section className="space-y-4 rounded-lg border p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 className="text-sm font-medium">{label}</h3>
        <Badge variant="medium">Changes proposed</Badge>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <div className="flex gap-2 lg:hidden" role="tablist" aria-label={`${label} comparison view`}>
          <Button
            type="button"
            size="sm"
            variant={mobileView === "before" ? "default" : "outline"}
            className="min-h-10 flex-1"
            role="tab"
            aria-selected={mobileView === "before"}
            onClick={() => setMobileView("before")}
          >
            Before
          </Button>
          <Button
            type="button"
            size="sm"
            variant={mobileView === "after" ? "default" : "outline"}
            className="min-h-10 flex-1"
            role="tab"
            aria-selected={mobileView === "after"}
            onClick={() => setMobileView("after")}
          >
            After
          </Button>
        </div>

        <div className={mobileView === "before" ? "block" : "hidden lg:block"}>
          <p className="mb-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
            Before
          </p>
          <div className="rounded-md border bg-muted/20 p-3">
            {sectionKey === "experience" || sectionKey === "projects"
              ? renderExperienceProjects(beforeValue)
              : (
                <p className="whitespace-pre-wrap text-sm line-through decoration-muted-foreground/60">
                  {formatSectionValue(beforeValue)}
                </p>
              )}
          </div>
        </div>

        <div className={mobileView === "after" ? "block" : "hidden lg:block"}>
          <p className="mb-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
            After
          </p>
          <div className="surface-success p-3">
            {sectionKey === "skills" ? (
              <div className="flex flex-wrap gap-2">
                {buildSkillReorderMeta(
                  formatSectionValue(beforeValue),
                  formatSectionValue(afterValue),
                ).map((item) => (
                  <span
                    key={item.skill}
                    className="inline-flex items-center gap-1 rounded-full border bg-background px-2 py-1 text-xs"
                  >
                    {item.skill}
                    {item.moved && item.previousIndex ? (
                      <span className="text-muted-foreground">
                        #{item.previousIndex}→#{item.currentIndex}
                      </span>
                    ) : null}
                  </span>
                ))}
              </div>
            ) : sectionKey === "experience" || sectionKey === "projects" ? (
              renderExperienceProjects(afterValue)
            ) : (
              <p className="whitespace-pre-wrap text-sm">
                {renderKeywordHighlights(
                  formatSectionValue(afterValue),
                  detectAddedKeywords(
                    formatSectionValue(beforeValue),
                    formatSectionValue(afterValue),
                  ),
                )}
              </p>
            )}
          </div>
        </div>
      </div>

      {sectionChanges.map((change) => {
        const decision = decisions[change.change_id] ?? "pending";
        const keywords = isSkillsReorderChange(change)
          ? []
          : detectAddedKeywords(change.before, change.after);

        return (
          <div key={change.change_id} className="rounded-md border p-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <p className="text-xs text-muted-foreground">
                {change.field_path ?? change.section}
              </p>
              <div className="flex gap-2">
                <Button
                  type="button"
                  size="sm"
                  className="min-h-10"
                  variant={decision === "accept" ? "default" : "outline"}
                  onClick={() => onDecision(change.change_id, "accept")}
                >
                  Accept
                </Button>
                <Button
                  type="button"
                  size="sm"
                  className="min-h-10"
                  variant={decision === "reject" ? "secondary" : "outline"}
                  onClick={() => onDecision(change.change_id, "reject")}
                >
                  Reject
                </Button>
              </div>
            </div>

            {!isSkillsReorderChange(change) && keywords.length > 0 ? (
              <div className="mt-2 flex flex-wrap gap-1">
                {keywords.map((keyword) => (
                  <Badge key={keyword} variant="low">
                    keyword: {keyword}
                  </Badge>
                ))}
              </div>
            ) : null}

            <ChangeWhyNote why={change.why} />
          </div>
        );
      })}
    </section>
  );
}
