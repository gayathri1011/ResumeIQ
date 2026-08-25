"use client";

import { useCallback, useRef, useState } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import { AlertCircle, CheckCircle2, FileText, Upload } from "lucide-react";

import { AppShell } from "@/components/layout/AppShell";
import { PageHeader } from "@/components/layout/PageHeader";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { UploadStepIndicator } from "@/features/resume/UploadStepIndicator";
import { getUserFriendlyErrorMessage } from "@/lib/error-messages";
import { MAX_UPLOAD_SIZE_MB } from "@/lib/constants";
import { cn } from "@/lib/utils";
import { uploadResume } from "@/services/resume.service";
import type { ResumeUploadResponse, UploadStage } from "@/types/resume";
import { SECTION_LABELS } from "@/types/resume";

const ACCEPTED_TYPES = [
  "application/pdf",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
  "image/png",
  "image/jpeg",
  "image/jpg",
  "image/webp",
  "image/gif",
];
const ACCEPTED_EXTENSIONS = [".pdf", ".docx", ".png", ".jpg", ".jpeg", ".webp", ".gif"];

function validateFile(file: File): string | null {
  const extension = file.name.toLowerCase().slice(file.name.lastIndexOf("."));
  if (!ACCEPTED_EXTENSIONS.includes(extension)) {
    return "Only PDF, DOCX, and image files (PNG, JPG, WEBP) are supported.";
  }
  if (
    file.type &&
    !ACCEPTED_TYPES.includes(file.type) &&
    file.type !== "application/octet-stream"
  ) {
    return "Only PDF, DOCX, and image files (PNG, JPG, WEBP) are supported.";
  }
  const maxBytes = MAX_UPLOAD_SIZE_MB * 1024 * 1024;
  if (file.size > maxBytes) {
    return `File exceeds the maximum size of ${MAX_UPLOAD_SIZE_MB} MB.`;
  }
  if (file.size === 0) {
    return "The selected file is empty.";
  }
  return null;
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function runPostUploadStages(
  setStage: (stage: UploadStage) => void,
): Promise<void> {
  const stubStages: UploadStage[] = ["understanding", "analyzing", "generating_insights"];
  for (const stage of stubStages) {
    setStage(stage);
    await sleep(stage === "understanding" ? 700 : 500);
  }
}

export function ResumeUploader() {
  const inputRef = useRef<HTMLInputElement>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [stage, setStage] = useState<UploadStage>("idle");
  const [uploadProgress, setUploadProgress] = useState(0);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [result, setResult] = useState<ResumeUploadResponse | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  const isProcessing = !["idle", "success", "error"].includes(stage);

  const reset = useCallback(() => {
    setStage("idle");
    setUploadProgress(0);
    setErrorMessage(null);
    setResult(null);
    setSelectedFile(null);
    if (inputRef.current) {
      inputRef.current.value = "";
    }
  }, []);

  const processFile = useCallback(async (file: File) => {
    const validationError = validateFile(file);
    if (validationError) {
      setErrorMessage(validationError);
      setStage("error");
      return;
    }

    setSelectedFile(file);
    setErrorMessage(null);
    setResult(null);
    setStage("uploading");
    setUploadProgress(0);

    try {
      const response = await uploadResume(file, (percent) => {
        setUploadProgress(percent);
        if (percent >= 100) {
          setStage("extracting");
        } else {
          setStage("uploading");
        }
      });

      await runPostUploadStages(setStage);
      setResult(response);
      setStage("success");
    } catch (error) {
      const message = getUserFriendlyErrorMessage(
        error,
        "Something went wrong while uploading your resume. Please try again.",
      );
      setErrorMessage(message);
      setStage("error");
    }
  }, []);

  const onFileSelected = useCallback(
    (files: FileList | null) => {
      const file = files?.[0];
      if (file) {
        void processFile(file);
      }
    },
    [processFile],
  );

  const onDrop = useCallback(
    (event: React.DragEvent<HTMLDivElement>) => {
      event.preventDefault();
      setIsDragging(false);
      onFileSelected(event.dataTransfer.files);
    },
    [onFileSelected],
  );

  return (
    <AppShell>
      <div className="mx-auto w-full max-w-2xl space-y-6">
        <PageHeader
          title="Upload resume"
          description="Upload a PDF, DOCX, or image resume (PNG, JPG, WEBP). We'll extract its structure, then you can run AI analysis from the dashboard."
          backHref="/dashboard"
        />
      <Card>
        <CardContent className="space-y-6">
          {stage === "idle" && (
            <div
              role="button"
              tabIndex={0}
              onDragOver={(e) => {
                e.preventDefault();
                setIsDragging(true);
              }}
              onDragLeave={() => setIsDragging(false)}
              onDrop={onDrop}
              onClick={() => inputRef.current?.click()}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") {
                  inputRef.current?.click();
                }
              }}
              className={cn(
                "flex cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed p-10 transition-colors",
                isDragging
                  ? "border-primary bg-primary/5"
                  : "border-muted-foreground/30 hover:border-primary/50",
              )}
            >
              <Upload className="mb-3 h-10 w-10 text-muted-foreground" />
              <p className="text-sm font-medium sm:hidden">Tap to choose a file</p>
              <p className="hidden text-sm font-medium sm:block">Drag and drop your resume here</p>
              <p className="mt-1 text-xs text-muted-foreground">
                PDF, DOCX, or image (PNG, JPG, WEBP), max {MAX_UPLOAD_SIZE_MB} MB
              </p>
              <input
                ref={inputRef}
                type="file"
                accept=".pdf,.docx,.png,.jpg,.jpeg,.webp,.gif,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,image/png,image/jpeg,image/webp,image/gif"
                className="hidden"
                onChange={(e) => onFileSelected(e.target.files)}
              />
            </div>
          )}

          {isProcessing && (
            <div className="rounded-xl border bg-muted/30 p-6">
              <UploadStepIndicator
                currentStage={stage}
                uploadProgress={uploadProgress}
              />
              {selectedFile && (
                <p className="mt-4 truncate text-xs text-muted-foreground">
                  {selectedFile.name}
                </p>
              )}
            </div>
          )}

          {stage === "success" && result && (
            <motion.div
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.35 }}
              className="surface-success space-y-4 p-6"
            >
              <div className="flex items-start gap-3">
                <CheckCircle2 className="mt-0.5 h-5 w-5 text-success" aria-hidden="true" />
                <div>
                  <p className="font-medium">Resume uploaded successfully</p>
                  <p className="text-sm text-muted-foreground">
                    {result.title} — {(result.file_size_bytes / 1024).toFixed(1)} KB
                  </p>
                </div>
              </div>

              {result.sections_found.length > 0 && (
                <div>
                  <p className="mb-2 text-sm font-medium">Sections found</p>
                    <div className="flex flex-wrap gap-2">
                    {[...new Set(result.sections_found)].map((section) => (
                      <span
                        key={section}
                        className="rounded-full bg-success/10 px-3 py-1 text-xs font-medium text-success"
                      >
                        {SECTION_LABELS[section] ?? section}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {result.sections_missing.length > 0 && (
                <p className="text-xs text-muted-foreground">
                  Not detected:{" "}
                  {result.sections_missing
                    .map((s) => SECTION_LABELS[s] ?? s)
                    .join(", ")}
                </p>
              )}

              <div className="flex flex-wrap gap-2">
                <Button asChild>
                  <Link href={`/dashboard?resumeId=${result.id}`}>
                    View dashboard
                  </Link>
                </Button>
                <Button variant="outline" onClick={reset}>
                  Upload another resume
                </Button>
              </div>
            </motion.div>
          )}

          {stage === "error" && (
            <div className="surface-error space-y-4 p-6">
              <div className="flex items-start gap-3">
                <AlertCircle className="mt-0.5 h-5 w-5 text-destructive" />
                <div>
                  <p className="font-medium text-destructive">Upload failed</p>
                  <p className="text-sm text-destructive/90">{errorMessage}</p>
                </div>
              </div>
              <Button onClick={reset}>Try again</Button>
            </div>
          )}
        </CardContent>
      </Card>
      </div>
    </AppShell>
  );
}
