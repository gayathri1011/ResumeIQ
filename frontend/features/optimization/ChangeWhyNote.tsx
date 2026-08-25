"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";

interface ChangeWhyNoteProps {
  why: string;
}

export function ChangeWhyNote({ why }: ChangeWhyNoteProps) {
  const [open, setOpen] = useState(false);

  return (
    <div className="mt-2">
      <Button
        type="button"
        variant="ghost"
        size="sm"
        className="h-7 px-2 text-xs text-muted-foreground"
        onClick={() => setOpen((value) => !value)}
      >
        Why was this changed?
      </Button>
      {open && (
        <p className="mt-1 rounded-xl border border-border/70 bg-gradient-to-b from-card to-muted/40 px-3 py-2 text-xs leading-relaxed text-muted-foreground shadow-[inset_0_1px_0_rgba(255,255,255,0.65)]">
          {why}
        </p>
      )}
    </div>
  );
}
