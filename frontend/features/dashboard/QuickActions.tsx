import Link from "next/link";
import {
  Briefcase,
  Upload,
  Wand2,
} from "lucide-react";

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
    key: "improve",
    label: "Improve Bullets",
    description: "AI rewrite for individual resume bullets",
    href: "/bullets/improve",
    icon: Wand2,
  },
] as const;

const VERSION_SCOPED_KEYS = new Set([
  "analyze_job",
  "improve",
]);

export function QuickActions({ resumeId, versionId }: QuickActionsProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Quick actions</CardTitle>
        <CardDescription>Common next steps for your resume</CardDescription>
      </CardHeader>
      <CardContent className="grid gap-3 sm:grid-cols-2">
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
              className="h-auto justify-start gap-3 px-4 py-3 text-left"
              asChild
            >
              <Link href={href}>
                <span className="icon-orb h-9 w-9 shrink-0">
                  <Icon className="h-4 w-4" aria-hidden="true" />
                </span>
                <span>
                  <span className="block text-sm font-medium">{action.label}</span>
                  <span className="block text-xs font-normal text-muted-foreground">
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
