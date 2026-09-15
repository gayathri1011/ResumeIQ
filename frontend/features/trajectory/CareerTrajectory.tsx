"use client";

import { useState } from "react";
import { ArrowRight, Compass, Loader2, Target } from "lucide-react";

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
import { CircularScore } from "@/features/dashboard/CircularScore";
import { getUserFriendlyErrorMessage } from "@/lib/error-messages";
import { analyzeCareerTrajectory } from "@/services/trajectory.service";
import type { CareerTrajectory, TrajectoryPath } from "@/types/trajectory";

interface CareerTrajectoryProps {
  resumeId: string;
  versionId?: string | null;
  available: boolean;
}

function TagGroup({
  title,
  items,
  variant = "secondary",
}: {
  title: string;
  items: string[];
  variant?: "secondary" | "outline" | "success";
}) {
  return (
    <div className="space-y-2">
      <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">{title}</p>
      {items.length === 0 ? (
        <p className="text-sm text-muted-foreground">None identified from this resume.</p>
      ) : (
        <div className="flex flex-wrap gap-2">
          {items.map((item) => <Badge key={item} variant={variant}>{item}</Badge>)}
        </div>
      )}
    </div>
  );
}

function PathDetails({ path }: { path: TrajectoryPath }) {
  return (
    <div className="space-y-5 border-t border-border/60 pt-5">
      <div className="grid gap-4 sm:grid-cols-2">
        <TagGroup title="Skills already shown" items={path.matched_skills} variant="success" />
        <TagGroup title="Skill gaps" items={path.skill_gaps} variant="outline" />
      </div>
      <TagGroup title="Proof gaps" items={path.proof_gaps} variant="outline" />
      <div className="space-y-3">
        <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Readiness breakdown</p>
        <div className="grid gap-3 sm:grid-cols-2">
          {path.factors.map((factor) => (
            <div key={factor.key} className="space-y-1.5">
              <div className="flex items-center justify-between text-xs">
                <span>{factor.label}</span>
                <span className="font-semibold tabular-nums">{factor.score}%</span>
              </div>
              <div className="h-2 overflow-hidden rounded-full bg-muted">
                <div className="h-full rounded-full bg-primary transition-all" style={{ width: `${factor.score}%` }} />
              </div>
              <p className="text-xs leading-relaxed text-muted-foreground">{factor.explanation}</p>
            </div>
          ))}
        </div>
      </div>
      <div className="space-y-2">
        <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Next steps</p>
        <ul className="space-y-2 text-sm text-muted-foreground">
          {path.next_steps.map((step) => <li key={step} className="flex gap-2"><ArrowRight className="mt-0.5 h-4 w-4 shrink-0 text-primary" />{step}</li>)}
        </ul>
      </div>
    </div>
  );
}

export function CareerTrajectory({ resumeId, versionId, available }: CareerTrajectoryProps) {
  const [result, setResult] = useState<CareerTrajectory | null>(null);
  const [selectedRole, setSelectedRole] = useState(0);
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const runAnalysis = async () => {
    setLoading(true);
    setErrorMessage(null);
    try {
      const response = await analyzeCareerTrajectory(resumeId, versionId);
      setResult(response);
      setSelectedRole(0);
    } catch (error) {
      setErrorMessage(getUserFriendlyErrorMessage(error, "Could not map your career trajectory. Please try again."));
    } finally {
      setLoading(false);
    }
  };

  const selectedPath = result?.paths[selectedRole];

  return (
    <Card>
      <CardHeader className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <CardTitle className="flex items-center gap-2"><span className="icon-orb h-9 w-9"><Compass className="h-4 w-4" /></span>Career trajectory</CardTitle>
          <CardDescription className="mt-2">Discover where your career can go next, based on the evidence in this resume.</CardDescription>
        </div>
        <Button variant="outline" onClick={() => void runAnalysis()} disabled={!available || loading}>
          {loading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Target className="mr-2 h-4 w-4" />}
          {loading ? "Mapping paths" : result ? "Refresh paths" : "Map my trajectory"}
        </Button>
      </CardHeader>
      <CardContent className="space-y-5">
        {!available ? <Alert variant="info">Run resume analysis first to ground career paths in your latest resume evidence.</Alert> : null}
        {errorMessage ? <Alert variant="error">{errorMessage}</Alert> : null}
        {result ? (
          <>
            <div className="rounded-xl border border-border/60 bg-muted/25 p-4">
              <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Current profile</p>
              <p className="mt-1 font-display text-2xl">{result.current_profile}</p>
              <p className="mt-2 max-w-3xl text-sm leading-relaxed text-muted-foreground">{result.profile_summary}</p>
            </div>
            <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
              {result.paths.map((path, index) => (
                <button
                  key={`${path.role}-${index}`}
                  type="button"
                  onClick={() => setSelectedRole(index)}
                  className={`rounded-xl border p-4 text-left transition ${selectedRole === index ? "border-primary/50 bg-primary/5 shadow-sm" : "border-border/70 bg-card hover:border-primary/30"}`}
                  aria-pressed={selectedRole === index}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div><p className="font-medium">{path.role}</p><p className="mt-1 text-xs text-muted-foreground">{path.timeframe}</p></div>
                    <CircularScore score={path.readiness_score} size={58} strokeWidth={5} />
                  </div>
                  <p className="mt-3 line-clamp-3 text-xs leading-relaxed text-muted-foreground">{path.summary}</p>
                </button>
              ))}
            </div>
            {selectedPath ? <PathDetails path={selectedPath} /> : null}
            {result.limitations.length > 0 ? <p className="text-xs leading-relaxed text-muted-foreground">Based on resume evidence only: {result.limitations.join(" ")}</p> : null}
          </>
        ) : (
          <div className="flex items-center gap-3 rounded-xl border border-dashed border-border p-5 text-sm text-muted-foreground">
            <Compass className="h-5 w-5 shrink-0 text-primary" />
            Your existing resume is enough. ResumeIQ will identify adjacent roles, explain readiness, and separate capability gaps from proof gaps.
          </div>
        )}
      </CardContent>
    </Card>
  );
}
