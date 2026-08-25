import { RefreshCw } from "lucide-react";

import { Alert } from "@/components/ui/alert";
import { AppShell } from "@/components/layout/AppShell";
import { Button } from "@/components/ui/button";

interface DashboardErrorProps {
  message: string;
  onRetry: () => void;
}

export function DashboardError({ message, onRetry }: DashboardErrorProps) {
  return (
    <AppShell className="flex min-h-[calc(100vh-3.5rem)] items-center justify-center">
      <div className="w-full max-w-lg space-y-4">
        <Alert variant="error" title="Couldn't load dashboard">
          {message}
        </Alert>
        <Button onClick={onRetry} variant="outline">
          <RefreshCw className="mr-2 h-4 w-4" aria-hidden="true" />
          Try again
        </Button>
      </div>
    </AppShell>
  );
}
