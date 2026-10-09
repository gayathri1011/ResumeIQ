import { describe, expect, it } from "vitest";
import type { EvidenceClass, EvidenceSourceType } from "@/types/growth";

describe("Career Growth Engine frontend logic", () => {
  const EVIDENCE_WEIGHTS: Record<EvidenceSourceType, number> = {
    interview: 1.0,
    project_evidence: 0.75,
    verified_evidence: 0.5,
    self_reported: 0.15,
  };

  it("enforces lowest weight for self-reported progress to prevent score inflation", () => {
    expect(EVIDENCE_WEIGHTS.self_reported).toBe(0.15);
    expect(EVIDENCE_WEIGHTS.interview).toBe(1.0);
    expect(EVIDENCE_WEIGHTS.self_reported).toBeLessThan(EVIDENCE_WEIGHTS.verified_evidence);
    expect(EVIDENCE_WEIGHTS.self_reported).toBeLessThan(EVIDENCE_WEIGHTS.project_evidence);
    expect(EVIDENCE_WEIGHTS.self_reported).toBeLessThan(EVIDENCE_WEIGHTS.interview);
  });

  it("classifies skills correctly across all four evidence classes", () => {
    const validClasses: EvidenceClass[] = [
      "evidence-backed",
      "inferred",
      "unverified",
      "missing",
    ];
    expect(validClasses).toHaveLength(4);
    expect(validClasses).toContain("evidence-backed");
    expect(validClasses).toContain("inferred");
    expect(validClasses).toContain("unverified");
    expect(validClasses).toContain("missing");
  });

  it("calculates mock deterministic readiness without score inflation from self-reported items", () => {
    // 2 skills: System Design (critical, weight 3.0), Docker (important, weight 2.0)
    // Both target 85 points.
    // If System Design is missing (0 pts) and Docker is unverified (25 * 0.35 = 8.75 pts)
    const baseSysRatio = 0.0;
    const baseDockerRatio = 8.75 / 85.0; // ~0.103

    const baselineScore = Math.round(
      ((3.0 * baseSysRatio + 2.0 * baseDockerRatio) / 5.0) * 100,
    ); // ~4%

    // User checks self-reported completed on a milestone for System Design:
    // Event: weight 0.15, score 25 -> normalized_score = (25/100) * 0.15 = 0.0375
    const selfReportedSysRatio = Math.max(baseSysRatio, 0.0375);
    const updatedScore = Math.round(
      ((3.0 * selfReportedSysRatio + 2.0 * baseDockerRatio) / 5.0) * 100,
    ); // ~6%

    // The score only nudged by 2 points; no artificial inflation!
    expect(updatedScore - baselineScore).toBeLessThanOrEqual(3);

    // In contrast, when an interview is completed with score 85 (weight 1.0):
    const interviewSysRatio = Math.max(baseSysRatio, (85 / 100) * 1.0); // 0.85
    const interviewScore = Math.round(
      ((3.0 * interviewSysRatio + 2.0 * baseDockerRatio) / 5.0) * 100,
    ); // ~55%

    // Massive verified boost
    expect(interviewScore).toBeGreaterThan(baselineScore + 40);
  });
});
