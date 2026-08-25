"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";

import { getUserFriendlyErrorMessage } from "@/lib/error-messages";
import {
  analyzeResume,
  getResume,
  listResumes,
} from "@/services/analysis.service";
import type { ResumeDetail, ResumeListItem } from "@/types/analysis";

export type DashboardStatus =
  | "loading"
  | "empty"
  | "error"
  | "ready"
  | "no_analysis";

interface DashboardData {
  resumes: ResumeListItem[];
  resume: ResumeDetail;
  selectedResumeId: string;
  selectedVersionId: string | null;
}

export function useDashboard() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const resumeIdParam = searchParams.get("resumeId");
  const versionIdParam = searchParams.get("versionId");

  const [status, setStatus] = useState<DashboardStatus>("loading");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [data, setData] = useState<DashboardData | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);

  const load = useCallback(async () => {
    setStatus("loading");
    setErrorMessage(null);

    try {
      const resumes = await listResumes();
      if (resumes.length === 0) {
        setData(null);
        setStatus("empty");
        return;
      }

      const sorted = [...resumes].sort(
        (a, b) =>
          new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime(),
      );

      const mostRecent = sorted[0];
      if (!mostRecent) {
        setData(null);
        setStatus("empty");
        return;
      }

      const selectedResumeId =
        resumeIdParam && sorted.some((r) => r.id === resumeIdParam)
          ? resumeIdParam
          : mostRecent.id;

      if (selectedResumeId !== resumeIdParam) {
        const query = new URLSearchParams({ resumeId: selectedResumeId });
        if (versionIdParam) query.set("versionId", versionIdParam);
        router.replace(`/dashboard?${query.toString()}`);
      }

      const resume = await getResume(selectedResumeId, versionIdParam);
      setData({
        resumes: sorted,
        resume,
        selectedResumeId,
        selectedVersionId: versionIdParam ?? resume.active_version_id ?? null,
      });
      setStatus(resume.latest_analysis ? "ready" : "no_analysis");
    } catch (error) {
      const message = getUserFriendlyErrorMessage(
        error,
        "Something went wrong while loading your dashboard.",
      );
      setErrorMessage(message);
      setStatus("error");
    }
  }, [resumeIdParam, versionIdParam, router]);

  useEffect(() => {
    void load();
  }, [load]);

  const selectResume = useCallback(
    (resumeId: string) => {
      router.push(`/dashboard?resumeId=${resumeId}`);
    },
    [router],
  );

  const runAnalysis = useCallback(async () => {
    if (!data) return;
    setIsAnalyzing(true);
    setErrorMessage(null);
    try {
      await analyzeResume(data.selectedResumeId, data.selectedVersionId);
      await load();
    } catch (error) {
      const message = getUserFriendlyErrorMessage(error, "Analysis failed. Please try again.");
      setErrorMessage(message);
    } finally {
      setIsAnalyzing(false);
    }
  }, [data, load]);

  return {
    status,
    errorMessage,
    data,
    isAnalyzing,
    load,
    selectResume,
    runAnalysis,
  };
}
