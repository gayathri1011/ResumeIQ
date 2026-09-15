import Link from "next/link";
import { Briefcase, Compass, Eye, Upload } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

interface QuickActionsProps {
  resumeId?: string;
  versionId?: string | null;
}

const ACTIONS = [
  {
    key: "upload",
    label: "Upload Resume",
    description: "Add or replace your resume file",
    href: "/resumes/upload",
    icon: Upload,
  },
  {
    key: "analyze_job",
    label: "Analyze Job",
    description: "Extract requirements from a job posting",
    href: "/jobs/analyze",
    icon: Briefcase,
  },
  {
    key: "career_trajectory",
    label: "Career Trajectory",
    description: "Discover where your career can go next",
    href: "/career-trajectory",
    icon: Compass,
  },
  {
    key: "recruiter_lens",
    label: "Recruiter Lens",
    description: "See what stands out in 10 seconds",
    href: "/recruiter-lens",
    icon: Eye,
  },
] as const;

const VERSION_SCOPED_KEYS = new Set([
  "analyze_job",
  "career_trajectory",
  "recruiter_lens",
]);

export function QuickActions({ resumeId, versionId }: QuickActionsProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Quick actions</CardTitle>
        <CardDescription>Common next steps for your resume</CardDescription>
      </CardHeader>
      <CardContent className="grid min-w-0 auto-rows-fr gap-3 sm:grid-cols-2 xl:grid-cols-4">
        {ACTIONS.map((action) => {
          const Icon = action.icon;
          const scoped =
            VERSION_SCOPED_KEYS.has(action.key) && resumeId;
          const href = scoped
            ? `${action.href}?resumeId=${resumeId}${versionId ? `&versionId=${versionId}` : ""}`
            : action.href;

          return (
            <Button
              key={action.key}
              variant="outline"
              className="h-full min-w-0 w-full justify-start gap-3 whitespace-normal px-4 py-3 text-left"
              asChild
            >
              <Link href={href} className="flex min-w-0 w-full items-center">
                <span className="icon-orb h-9 w-9 shrink-0">
                  <Icon className="h-4 w-4" aria-hidden="true" />
                </span>
                <span className="min-w-0 flex-1 break-words">
                  <span className="block break-words text-sm font-medium">{action.label}</span>
                  <span className="block break-words text-xs font-normal text-muted-foreground">
                    {action.description}
                  </span>
                </span>
              </Link>
            </Button>
          );
        })}
      </CardContent>
    </Card>
  );
}
