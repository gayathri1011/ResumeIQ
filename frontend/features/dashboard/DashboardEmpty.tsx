import Link from "next/link";
import { FileUp } from "lucide-react";

import { AppShell } from "@/components/layout/AppShell";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

export function DashboardEmpty() {
  return (
    <AppShell className="flex min-h-[calc(100vh-3.5rem)] items-center justify-center">
      <Card className="w-full max-w-lg">
        <CardHeader className="text-center">
          <div className="mx-auto mb-2 flex h-12 w-12 items-center justify-center rounded-full bg-muted">
            <FileUp className="h-6 w-6 text-muted-foreground" aria-hidden="true" />
          </div>
          <CardTitle>No resumes yet</CardTitle>
          <CardDescription>
            Upload a resume to parse its structure and run AI analysis. Your
            dashboard will show health scores and actionable feedback.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex justify-center">
          <Button asChild>
            <Link href="/resumes/upload">Upload your first resume</Link>
          </Button>
        </CardContent>
      </Card>
    </AppShell>
  );
}
