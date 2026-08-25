"use client";

import { useCallback, useState } from "react";
import { Download, Loader2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { getUserFriendlyErrorMessage } from "@/lib/error-messages";
import { generateVersionPdf } from "@/lib/download";

interface DownloadPdfButtonProps {
  resumeId: string;
  versionId: string;
  versionLabel?: string | null;
  size?: "sm" | "default";
  variant?: "default" | "outline" | "secondary" | "ghost";
  className?: string;
}

export function DownloadPdfButton({
  resumeId,
  versionId,
  versionLabel,
  size = "sm",
  variant = "outline",
  className,
}: DownloadPdfButtonProps) {
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const handleDownload = useCallback(async () => {
    setLoading(true);
    setErrorMessage(null);
    try {
      await generateVersionPdf(resumeId, versionId, versionLabel);
    } catch (error) {
      const message = getUserFriendlyErrorMessage(
        error,
        "Could not generate the PDF. Please try again.",
      );
      setErrorMessage(message);
    } finally {
      setLoading(false);
    }
  }, [resumeId, versionId, versionLabel]);

  return (
    <div className={className}>
      <Button
        size={size}
        variant={variant}
        onClick={() => void handleDownload()}
        disabled={loading}
      >
        {loading ? (
          <Loader2 className="mr-1 h-3.5 w-3.5 animate-spin" />
        ) : (
          <Download className="mr-1 h-3.5 w-3.5" />
        )}
        {loading ? "Generating…" : "Download PDF"}
      </Button>
      {errorMessage ? (
        <p className="mt-1 text-xs text-red-600 dark:text-red-400">{errorMessage}</p>
      ) : null}
    </div>
  );
}
