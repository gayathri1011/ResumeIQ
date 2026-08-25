"use client";

import { Check, Circle, Loader2 } from "lucide-react";

import { cn } from "@/lib/utils";
import type { JobAnalyzeStage } from "@/types/job";
import { JOB_ANALYZE_STAGES } from "@/types/job";

const STAGE_ORDER: JobAnalyzeStage[] = ["reading", "extracting", "done"];

function stageIndex(stage: JobAnalyzeStage): number {
  if (stage === "idle" || stage === "error") return -1;
  if (stage === "done") return STAGE_ORDER.length;
  return STAGE_ORDER.indexOf(stage);
}

interface JobStepIndicatorProps {
  currentStage: JobAnalyzeStage;
}

export function JobStepIndicator({ currentStage }: JobStepIndicatorProps) {
  const activeIndex = stageIndex(currentStage);

  return (
    <ul className="space-y-3">
      {JOB_ANALYZE_STAGES.map((step, index) => {
        const isComplete = activeIndex > index || currentStage === "done";
        const isActive = activeIndex === index && currentStage !== "done";
        const isPending = activeIndex < index && currentStage !== "done";

        return (
          <li key={step.key} className="flex items-center gap-3">
            <span
              className={cn(
                "flex h-8 w-8 items-center justify-center rounded-full border",
                isComplete && "border-primary bg-primary text-primary-foreground",
                isActive && "border-primary text-primary",
                isPending && "border-muted-foreground/30 text-muted-foreground",
              )}
            >
              {isComplete ? (
                <Check className="h-4 w-4" />
              ) : isActive ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Circle className="h-3 w-3" />
              )}
            </span>
            <p
              className={cn(
                "text-sm font-medium",
                isPending && "text-muted-foreground",
              )}
            >
              {step.label}
            </p>
          </li>
        );
      })}
    </ul>
  );
}
