"use client";

import { Check, Circle, Loader2 } from "lucide-react";

import { cn } from "@/lib/utils";
import type { UploadStage } from "@/types/resume";
import { UPLOAD_STAGES } from "@/types/resume";

const STAGE_ORDER: UploadStage[] = [
  "uploading",
  "extracting",
  "understanding",
  "analyzing",
  "generating_insights",
];

function stageIndex(stage: UploadStage): number {
  if (stage === "idle" || stage === "error") return -1;
  if (stage === "success") return STAGE_ORDER.length;
  return STAGE_ORDER.indexOf(stage);
}

interface UploadStepIndicatorProps {
  currentStage: UploadStage;
  uploadProgress?: number;
}

export function UploadStepIndicator({
  currentStage,
  uploadProgress = 0,
}: UploadStepIndicatorProps) {
  const activeIndex = stageIndex(currentStage);

  return (
    <div className="space-y-4">
      <ul className="space-y-3">
        {UPLOAD_STAGES.map((step, index) => {
          const isComplete = activeIndex > index || currentStage === "success";
          const isActive = activeIndex === index && currentStage !== "success";
          const isPending = activeIndex < index && currentStage !== "success";

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
              <div className="flex-1">
                <p
                  className={cn(
                    "text-sm font-medium",
                    isPending && "text-muted-foreground",
                  )}
                >
                  {step.label}
                </p>
                {isActive && step.key === "uploading" && uploadProgress > 0 && (
                  <p className="text-xs text-muted-foreground">{uploadProgress}%</p>
                )}
              </div>
            </li>
          );
        })}
      </ul>

      {currentStage === "uploading" && uploadProgress > 0 && (
        <div className="h-2 w-full overflow-hidden rounded-full bg-muted">
          <div
            className="h-full rounded-full bg-primary transition-all duration-300"
            style={{ width: `${uploadProgress}%` }}
          />
        </div>
      )}
    </div>
  );
}
